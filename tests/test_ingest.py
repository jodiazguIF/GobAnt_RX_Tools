import os
import sys
import pathlib
import types
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
sys.modules.setdefault("google", types.ModuleType("google"))
sys.modules.setdefault("google.genai", types.ModuleType("google.genai"))
from app.pipeline.ingest import IngestPipeline
from app.config import settings

def test_has_cache_for_file(tmp_path):
    pipeline = IngestPipeline.__new__(IngestPipeline)
    old_out = settings.out_dir
    object.__setattr__(settings, 'out_dir', str(tmp_path))
    try:
        file_id = 'abc123def456'
        # No cache yet
        assert pipeline._has_cache_for_file(file_id) is False
        # Create cache file
        prefix = file_id[:8]
        cache_file = tmp_path / f'rad__{prefix}.json'
        cache_file.write_text('{}', encoding='utf-8')
        assert pipeline._has_cache_for_file(file_id) is True
    finally:
        object.__setattr__(settings, 'out_dir', old_out)
