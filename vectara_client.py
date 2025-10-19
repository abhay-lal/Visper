"""Vectara client for ingesting documents into Vectara corpus."""

import os
import logging
from typing import List, Dict, Any, Optional
import time
from vectara import Vectara, CoreDocument, CoreDocumentPart
from fastapi import HTTPException

# Configure logger
logger = logging.getLogger(__name__)

# File extensions to consider as text/code (allow ingestion)
TEXT_CODE_EXTENSIONS = {
    # Code files
    '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp',
    '.cs', '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.php', '.sh',
    '.bash', '.zsh', '.fish', '.ps1', '.r', '.lua', '.perl', '.pl',

    # Web files
    '.html', '.htm', '.css', '.scss', '.sass', '.less', '.vue', '.svelte',

    # Config/Data files
    '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
    '.env', '.properties', '.config',

    # Documentation
    '.md', '.markdown', '.rst', '.txt', '.adoc', '.tex',

    # Build/Project files
    '.gradle', '.maven', '.sbt', '.cmake', '.make', 'makefile',
    '.dockerfile', 'dockerfile',

    # Database/Query
    '.sql', '.graphql', '.prisma',
}

# Readme file patterns to filter out (keep only one)
README_PATTERNS = {
    'readme.md', 'readme', 'readme.txt', 'readme.rst',
    'read_me.md', 'read_me', 'read.me', 'readme.markdown'
}


class VectaraClient:
    """Client for interacting with Vectara API for document ingestion."""

    def __init__(
        self,
        corpus_key: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize the Vectara client.

        Args:
            corpus_key: Vectara corpus key. If not provided, reads from VECTARA_CORPUS_KEY env var.
            api_key: Vectara API key. If not provided, reads from VECTARA_API_KEY env var.

        Raises:
            HTTPException: If any required credentials are missing
        """
        self.corpus_key = corpus_key or os.getenv("VECTARA_CORPUS_KEY", "blindverse")
        self.api_key = api_key or os.getenv("VECTARA_API_KEY")

        # Validate credentials
        missing_creds = []
        if not self.api_key:
            missing_creds.append("VECTARA_API_KEY")

        if missing_creds:
            raise HTTPException(
                status_code=500,
                detail=f"Missing Vectara credentials: {', '.join(missing_creds)}. "
                       "Please set the environment variables."
            )

        # Initialize Vectara client with only api_key
        try:
            self.client = Vectara(api_key=self.api_key)
            logger.info(f"✅ Vectara client initialized successfully (corpus: {self.corpus_key})")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Vectara client: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize Vectara client: {str(e)}"
            )

    def should_ingest_file(self, file_data: Dict[str, Any]) -> bool:
        """
        Determine if a file should be ingested into Vectara.

        Args:
            file_data: Dictionary containing file metadata

        Returns:
            True if the file should be ingested, False otherwise
        """
        filename = file_data.get('name', '').lower()
        path = file_data.get('path', '').lower()
        content = file_data.get('content', '')

        # Skip if no content or error
        if not content or content.startswith('[Binary content') or 'Failed to fetch' in content:
            return False

        # Skip if content is too small (likely empty or placeholder)
        if len(content.strip()) < 10:
            return False

        # Get file extension
        extension = os.path.splitext(filename)[1].lower()

        # Handle files without extension (like Dockerfile, Makefile)
        if not extension:
            # Check if it's a known file without extension
            if filename in ['dockerfile', 'makefile', 'jenkinsfile', 'vagrantfile',
                           'gemfile', 'rakefile', 'procfile', 'license', 'gitignore']:
                return True
            return False

        # Only ingest text/code files
        if extension not in TEXT_CODE_EXTENSIONS:
            logger.info(f"⏩ Skipping non-text file: {path} (extension: {extension})")
            return False

        return True

    def filter_readme_files(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter README files to keep only one (preferably README.md from root).

        Args:
            files: List of file data dictionaries

        Returns:
            List of files with only one README file
        """
        readme_files = []
        other_files = []

        for file_data in files:
            filename = file_data.get('name', '').lower()
            path = file_data.get('path', '').lower()

            # Check if it's a README file
            is_readme = filename in README_PATTERNS

            if is_readme:
                readme_files.append(file_data)
            else:
                other_files.append(file_data)

        if not readme_files:
            return files

        # Prioritize README.md in root directory
        root_readme = None
        for readme in readme_files:
            if readme['path'].lower() == 'readme.md':
                root_readme = readme
                break

        # If no root README.md, take the first README found
        selected_readme = root_readme or readme_files[0]

        logger.info(f"📝 Keeping only one README file: {selected_readme['path']}")
        logger.info(f"   Filtered out {len(readme_files) - 1} other README files")

        return other_files + [selected_readme]

    def prepare_document(
        self,
        file_data: Dict[str, Any],
        owner: str,
        repo: str
    ) -> CoreDocument:
        """
        Prepare a document for Vectara ingestion using CoreDocument.

        Args:
            file_data: File data with content and metadata
            owner: Repository owner
            repo: Repository name

        Returns:
            CoreDocument object formatted for Vectara SDK v0.3.5
        """
        path = file_data.get('path', '')
        filename = file_data.get('name', '')
        content = file_data.get('content', '')
        size = file_data.get('size', 0)
        file_type = os.path.splitext(filename)[1].lstrip('.') or 'no_extension'

        # Create document ID (unique identifier)
        doc_id = f"{owner}/{repo}/{path}".replace('//', '/')

        # Prepare metadata for the document
        doc_metadata = {
            "repo": f"{owner}/{repo}",
            "owner": owner,
            "source": f"https://github.com/{owner}/{repo}/blob/main/{path}"
        }

        # Prepare metadata for the document part
        part_metadata = {
            "path": path,
            "file_name": filename,
            "file_type": file_type,
            "size": str(size)
        }

        # Create CoreDocument with CoreDocumentPart
        document = CoreDocument(
            id=doc_id,
            type="core",
            document_parts=[
                CoreDocumentPart(
                    text=content,
                    metadata=part_metadata
                )
            ],
            metadata=doc_metadata
        )

        return document

    async def ingest_document(
        self,
        document: CoreDocument,
        owner: str,
        repo: str,
        max_retries: int = 3
    ) -> bool:
        """
        Ingest a single document into Vectara with retry logic.

        Args:
            document: CoreDocument object formatted for Vectara
            owner: Repository owner
            repo: Repository name
            max_retries: Maximum number of retry attempts

        Returns:
            True if successful, False otherwise
        """
        doc_id = document.id

        for attempt in range(max_retries):
            try:
                # Use the correct Vectara SDK v0.3.5 API
                response = self.client.documents.create(
                    corpus_key=self.corpus_key,
                    request=document
                )

                logger.info(f"✅ Successfully ingested: {doc_id}")
                return True

            except Exception as e:
                logger.warning(f"⚠️  Attempt {attempt + 1}/{max_retries} failed for {doc_id}: {str(e)}")

                if attempt < max_retries - 1:
                    # Wait before retrying (exponential backoff)
                    wait_time = 2 ** attempt
                    logger.info(f"   Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ Failed to ingest {doc_id} after {max_retries} attempts")
                    return False

        return False

    async def ingest_files(
        self,
        files: List[Dict[str, Any]],
        owner: str,
        repo: str
    ) -> Dict[str, Any]:
        """
        Ingest multiple files into Vectara corpus.

        Args:
            files: List of file data dictionaries
            owner: Repository owner
            repo: Repository name

        Returns:
            Dictionary with ingestion statistics
        """
        logger.info(f"🚀 Starting Vectara ingestion for {owner}/{repo}")
        print(f"\n{'='*80}")
        print(f"🔄 VECTARA INGESTION - {owner}/{repo}")
        print(f"{'='*80}\n")

        # Filter README files
        filtered_files = self.filter_readme_files(files)

        # Filter files to ingest
        files_to_ingest = [f for f in filtered_files if self.should_ingest_file(f)]

        logger.info(f"📊 Files to ingest: {len(files_to_ingest)} out of {len(files)} total files")
        print(f"📊 Total files: {len(files)}")
        print(f"📊 Files to ingest: {len(files_to_ingest)}\n")

        if not files_to_ingest:
            logger.warning("⚠️  No files to ingest")
            print("⚠️  No files to ingest\n")
            return {
                "total_files": len(files),
                "ingested": 0,
                "skipped": len(files),
                "failed": 0
            }

        # Ingest each file
        successful = 0
        failed = 0

        for i, file_data in enumerate(files_to_ingest, 1):
            path = file_data.get('path', 'unknown')
            print(f"[{i}/{len(files_to_ingest)}] Ingesting: {path}")
            logger.info(f"[{i}/{len(files_to_ingest)}] Processing: {path}")

            try:
                # Prepare document
                document = self.prepare_document(file_data, owner, repo)

                # Ingest document with owner and repo parameters
                success = await self.ingest_document(document, owner, repo)

                if success:
                    successful += 1
                    print(f"   ✅ Success")
                else:
                    failed += 1
                    print(f"   ❌ Failed")

            except Exception as e:
                logger.error(f"❌ Error preparing/ingesting {path}: {str(e)}")
                print(f"   ❌ Error: {str(e)}")
                failed += 1

        # Summary
        skipped = len(files) - len(files_to_ingest)

        print(f"\n{'='*80}")
        print("📊 INGESTION SUMMARY")
        print(f"{'='*80}")
        print(f"✅ Successfully ingested: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"⏩ Skipped: {skipped}")
        print(f"📁 Total files: {len(files)}")
        print(f"{'='*80}\n")

        logger.info(f"✅ Ingestion complete: {successful} successful, {failed} failed, {skipped} skipped")

        return {
            "total_files": len(files),
            "ingested": successful,
            "skipped": skipped,
            "failed": failed
        }
