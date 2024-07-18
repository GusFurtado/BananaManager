from sqlalchemy import MetaData, Table, select, update

from ..models import get_table_model
from ..utils import db


class UpdateCellCallback:
    def __init__(self, data: list[dict[str, str]], pathname: str):
        # Validate data
        assert len(data) == 1, data

        self.col_id = data[0]["colId"]
        self.row_id = data[0]["rowId"]
        self.new_value = data[0]["value"]

        self.metadata = MetaData()
        _, group_name, table_name = pathname.split("/")
        self.banana_table = get_table_model(table_name, group_name)

    def exec(self):
        table_data = Table(
            self.banana_table.name,
            self.metadata,
            schema=self.banana_table.schema_name,
            autoload_with=db.engine,
        )

        banana_column = next(
            col for col in self.banana_table.columns if col.name == self.col_id
        )

        if banana_column.foreign_key is not None:
            foreign_table = Table(
                banana_column.foreign_key.table_name,
                self.metadata,
                schema=banana_column.foreign_key.schema_name,
                autoload_with=db.engine,
            )

            with db.engine.connect() as conn:
                id_col = foreign_table.c[banana_column.foreign_key.column_name]
                label = foreign_table.c[banana_column.foreign_key.column_display]

                query = (
                    select(id_col)
                    .select_from(foreign_table)
                    .where(label == self.new_value)
                )

                result = conn.execute(query)
                rows = result.fetchall()
                self.new_value = rows[0][0]

        with db.engine.connect() as conn:
            query = (
                update(table_data)
                .where(table_data.c[self.banana_table.primary_key.name] == self.row_id)
                .values({self.col_id: self.new_value})
            )
            conn.execute(query)
            conn.commit()
