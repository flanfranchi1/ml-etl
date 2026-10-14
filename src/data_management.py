from collections.abc import Iterator
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, ClassVar, get_args, get_origin, get_type_hints

from sqlalchemy import (
    DECIMAL,
    JSON,
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    select,
)
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
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
        primary_key_columns = tuple(table.primary_key.columns)

        with self.engine.begin() as connection:
            if primary_key_columns and all(
                column.name in values for column in primary_key_columns
            ):
                statement = sqlite_insert(table).values(values)
                update_values = {
                    column_name: getattr(statement.excluded, column_name)
                    for column_name in values
                    if column_name not in table.primary_key.columns.keys()
                }
                if update_values:
                    statement = statement.on_conflict_do_update(
                        index_elements=primary_key_columns,
                        set_=update_values,
                    )
                else:
                    statement = statement.on_conflict_do_nothing(
                        index_elements=primary_key_columns,
                    )
            else:
                statement = table.insert().values(values)

            connection.execute(statement)

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

    def create_table(self, entity: PersistableEntity | type[Any]) -> None:
        entity_type = entity if isinstance(entity, type) else type(entity)
        entity_name = entity_type.entity_name
        table = self.metadata.tables.get(entity_name)

        if table is None:
            type_conversion: dict[Any, Any] = {
                int: Integer,
                str: String,
                float: DECIMAL,
                Decimal: DECIMAL,
                bool: Boolean,
                datetime: DateTime,
                dict: JSON,
                list: JSON,
                Any: JSON,
            }
            type_hints = get_type_hints(entity_type)
            columns: list[Column[Any]] = []

            for field_name, field_type in type_hints.items():
                if get_origin(field_type) is ClassVar:
                    continue

                type_args = get_args(field_type)
                nullable = False
                column_type = None

                if type(None) in type_args:
                    nullable = True
                    field_types = tuple(
                        arg for arg in type_args if arg is not type(None)
                    )
                    if len(field_types) == 1:
                        field_type = field_types[0]
                    elif all(get_origin(arg) in (dict, list) for arg in field_types):
                        column_type = JSON
                    else:
                        raise TypeError(
                            f"Unsupported nullable type for "
                            f"{entity_name}.{field_name}: {field_type}"
                        )

                if column_type is None:
                    column_type = type_conversion.get(field_type)
                if column_type is None and get_origin(field_type) in (dict, list):
                    column_type = JSON
                if column_type is None:
                    raise TypeError(
                        f"Unsupported type for {entity_name}.{field_name}: {field_type}"
                    )

                is_primary_key = field_name == "id"
                columns.append(
                    Column(
                        field_name,
                        column_type,
                        primary_key=is_primary_key,
                        nullable=False if is_primary_key else nullable,
                    )
                )

            table = Table(entity_name, self.metadata, *columns)

        table.create(self.engine, checkfirst=True)
