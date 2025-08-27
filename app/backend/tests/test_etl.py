from pathlib import Path
import duckdb
from app.backend.etl.sheets_to_parquet import run_etl


def test_etl_creates_parquet(tmp_path):
    csv_content = (
        "RADICADO,FECHA,MUNICIPIO,SUBREGIÓN,TIPO DE EQUIPO,CATEGORÍA\n"
        "1,2024-01-01,Medellin,Valle de Aburrá,ODONTOLOGICO,FIJO\n"
    )
    csv_path = tmp_path / "licencias.csv"
    csv_path.write_text(csv_content, encoding="utf-8")
    run_etl(str(csv_path))
    parquet_path = Path("data/processed/licencias.parquet")
    assert parquet_path.exists()
    con = duckdb.connect()
    df = con.execute(f"SELECT * FROM read_parquet('{parquet_path}')").df()
    assert df['FECHA'].dtype.name.startswith('datetime')
    assert df.loc[0, 'MUNICIPIO_CODIGO'] == '05001'
    assert df.loc[0, 'SUBREGION_CODIGO'] == '01'
