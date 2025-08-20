from app.pipeline.ingest import IngestPipeline

if __name__ == "__main__":
    pipeline = IngestPipeline()
    #Seleccionar el adecuado para el trabajo deseados
    pipeline.process_folder()
    #pipeline.process_folder_only_new()