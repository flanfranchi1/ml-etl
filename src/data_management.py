from collections.abc import Iterator
from pathlib import Path
from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    select,
)
from sqlalchemy.engine import URL

from data_modeling import PersistableEntity


class DatabaseHandler:
    def __init__(self, db_path: Path) -> None:
        database_url = URL.create(
            "sqlite",
            database=str(db_path.resolve()),
        )

        self.engine = create_engine(database_url)
        self.metadata = MetaData()

        self.bronze_products = Table(
            "bronze_products",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("job_run", DateTime, nullable=False),
            Column("endpoint", String, nullable=False),
            Column("keywords", String, nullable=True),
            Column("results", JSON, nullable=False),
            Column("paging", JSON, nullable=False),
            Column("query_type", String),
        )

    def setup(self) -> None:
        self.metadata.create_all(self.engine)

    def close(self) -> None:
        self.engine.dispose()

    def insert(
        self,
        data: PersistableEntity,
    ) -> None:
        table = self.metadata.tables[data.entity_name]
        values: dict[str, Any] = data.as_dict()
        with self.engine.begin() as connection:
            connection.execute(
                table.insert(),
                values,
            )

    def retrieve_data(self, dm: type[PersistableEntity]) -> Iterator[dict[str, Any]]:
        table_name: str = dm.entity_name

        try:
            table = self.metadata.tables[table_name]
        except KeyError as e:
            raise ValueError("table %s not registered on database", table_name) from e

        with self.engine.connect() as conn:
            result = conn.execute(select(table)).mappings()

        for row in result:
            yield dict(row)
