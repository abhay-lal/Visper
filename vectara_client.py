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
            "size": str(size),
            "repo": f"{owner}/{repo}",  # Add repo to part metadata for filtering
            "owner": owner  # Add owner to part metadata for filtering
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

    async def search_corpus(
        self,
        query: str,
        limit: int = 5,
        repo_filter: Optional[str] = None,
        owner_filter: Optional[str] = None,
        enable_rag: bool = True
    ) -> Dict[str, Any]:
        """
        Search the Vectara corpus with natural language query.

        Args:
            query: Natural language search query
            limit: Maximum number of results to return (default: 5, max: 20)
            repo_filter: Optional filter by repository name (e.g., "owner/repo")
            owner_filter: Optional filter by repository owner
            enable_rag: Enable RAG/Generation mode for summary answer (default: True)

        Returns:
            Dictionary with search results including summary, sources, and metadata
        """
        import time
        start_time = time.time()

        logger.info(f"🔍 Searching Vectara corpus: '{query}'")
        logger.info(f"   Filters - repo: {repo_filter}, owner: {owner_filter}, limit: {limit}")

        try:
            # Prepare metadata filter
            # NOTE: Metadata filtering requires the corpus to have filterable attributes configured
            # For now, we'll skip filtering as the corpus may not have these attributes set up
            # To enable filtering, you need to configure filterable attributes in Vectara console
            filter_str = None

            # Log filter request if provided
            if repo_filter or owner_filter:
                logger.warning(f"⚠️  Metadata filters requested but not applied (corpus may not have filterable attributes configured)")
                logger.warning(f"   Requested filters - repo: {repo_filter}, owner: {owner_filter}")
                logger.warning(f"   To enable filtering, configure filterable attributes in Vectara console for fields: repo, owner")

            # Uncomment below when filterable attributes are configured:
            # if repo_filter and owner_filter:
            #     filter_str = f"doc.repo = '{owner_filter}/{repo_filter}'"
            # elif owner_filter:
            #     filter_str = f"doc.owner = '{owner_filter}'"
            # elif repo_filter:
            #     filter_str = f"doc.repo contains '{repo_filter}'"

            # Prepare search request using the correct Vectara SDK v0.3.5 API
            from vectara import SearchCorporaParameters, GenerationParameters, CitationParameters

            # Configure generation (RAG) parameters if enabled
            generation_params = None
            if enable_rag:
                generation_params = GenerationParameters(
                    generation_preset_name="vectara-summary-ext-v1.2.0",
                    max_used_search_results=min(limit, 10),
                    enable_factual_consistency_score=True,
                    citations=CitationParameters(
                        style="none"
                    )
                )

            # Build search parameters WITHOUT generation (it goes as separate param to query)
            search_params = SearchCorporaParameters(
                corpora=[{
                    "corpus_key": self.corpus_key,
                    "metadata_filter": filter_str if filter_str else None,
                    "lexical_interpolation": 0.025  # Slightly favor semantic search
                }],
                limit=min(limit, 20),  # Cap at 20 results
                offset=0
            )

            # Execute search using the SDK - generation is passed separately
            response = self.client.query(
                query=query,
                search=search_params,
                generation=generation_params  # Pass generation as separate parameter
            )

            # Calculate query time
            query_time_ms = int((time.time() - start_time) * 1000)

            # Parse response
            results = self._parse_search_response(response, query_time_ms)

            logger.info(f"✅ Search completed in {query_time_ms}ms - {results['total_results']} results")

            return results

        except Exception as e:
            logger.error(f"❌ Search error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Search failed: {str(e)}"
            )

    def _parse_search_response(
        self,
        response: Any,
        query_time_ms: int
    ) -> Dict[str, Any]:
        """
        Parse Vectara search response into a clean format.

        Args:
            response: Raw response from Vectara SDK
            query_time_ms: Query execution time in milliseconds

        Returns:
            Formatted search results dictionary
        """
        result = {
            "summary": None,
            "sources": [],
            "total_results": 0,
            "query_time_ms": query_time_ms
        }

        try:
            # Extract summary from generation (RAG)
            if hasattr(response, 'summary') and response.summary:
                result["summary"] = response.summary

            # Extract search results
            if hasattr(response, 'search_results') and response.search_results:
                search_results = response.search_results
                result["total_results"] = len(search_results)

                # Process each search result
                for search_result in search_results:
                    try:
                        # Extract document metadata
                        doc_metadata = {}
                        part_metadata = {}

                        # Get document-level metadata
                        if hasattr(search_result, 'document_metadata'):
                            doc_metadata = search_result.document_metadata or {}

                        # Get part-level metadata
                        if hasattr(search_result, 'part_metadata'):
                            part_metadata = search_result.part_metadata or {}

                        # Extract text snippet
                        text = ""
                        if hasattr(search_result, 'text'):
                            text = search_result.text or ""

                        # Extract score
                        score = 0.0
                        if hasattr(search_result, 'score'):
                            score = float(search_result.score or 0.0)

                        # Build source object
                        source = {
                            "file_path": part_metadata.get("path", "Unknown"),
                            "file_name": part_metadata.get("file_name", "Unknown"),
                            "file_type": part_metadata.get("file_type", "Unknown"),
                            "repo": doc_metadata.get("repo", "Unknown"),
                            "owner": doc_metadata.get("owner", "Unknown"),
                            "source_url": doc_metadata.get("source", ""),
                            "relevance_score": round(score, 4),
                            "snippet": text[:200] + "..." if len(text) > 200 else text
                        }

                        result["sources"].append(source)

                    except Exception as e:
                        logger.warning(f"⚠️  Error parsing search result: {str(e)}")
                        continue

        except Exception as e:
            logger.error(f"❌ Error parsing search response: {str(e)}")
            # Return partial results if available
            pass

        return result
