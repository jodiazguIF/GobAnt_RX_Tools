from app.pipeline.ingest import IngestPipeline

if __name__ == "__main__":
    pipeline = IngestPipeline()
    pipeline.process_folder()