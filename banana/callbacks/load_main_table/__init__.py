from dash.exceptions import PreventUpdate
from sqlalchemy import MetaData, Table, select

from .main_table_query import MainTableQuery
from ...core.instances import db
from ...core.io import read_sql
from ...core.utils import split_pathname
from ...models.table_models import BananaColumn, get_table_model


class LoadMainTableCallback:
    def __init__(self, pathname: str):
        group_name, table_name = split_pathname(pathname)
        if table_name is None:
            raise PreventUpdate

        self.banana_table = get_table_model(group_name, table_name)

    def __get_columnDef(self, column: BananaColumn) -> dict[str, str]:
        if column.foreign_key is None:
            col_def = {"headerName": column.display_name, "field": column.name}
            col_def.update(column.columnDef)
            return col_def

        else:
            metadata = MetaData()
            foreign_table = Table(
                column.foreign_key.table_name,
                metadata,
                schema=column.foreign_key.schema_name,
                autoload_with=db.engine,
            )

            query = select(foreign_table.c[column.foreign_key.column_display])
            query = query.select_from(foreign_table)

            if column.foreign_key.order_by is not None:
                for orderby_col in column.foreign_key.order_by:
                    if orderby_col.desc:
                        orderby = foreign_table.c[orderby_col.column].desc()
                    else:
                        orderby = foreign_table.c[orderby_col.column].asc()
                    query = query.order_by(orderby)

            rows = read_sql(query)
            col_def = {
                "headerName": column.display_name,
                "field": column.name,
                "cellEditor": "agSelectCellEditor",
                "cellEditorParams": {"values": [row[0] for row in rows]},
            }
            col_def.update(column.columnDef)
            return col_def

    @property
    def columnDefs(self) -> list[dict]:
        id_col = {
            "headerName": self.banana_table.primary_key.display_name,
            "field": self.banana_table.primary_key.name,
            "editable": False,
        }
        id_col.update(self.banana_table.primary_key.columnDef)

        values_cols = [self.__get_columnDef(col) for col in self.banana_table.columns]
        return [id_col] + values_cols

    @property
    def rowData(self):
        sqlalchemy_table = MainTableQuery(self.banana_table)
        rows = read_sql(sqlalchemy_table.query)

        # Define Rows
        cols = [self.banana_table.primary_key.name] + [
            col.name for col in self.banana_table.columns
        ]
        row_data = []
        for row in rows:
            row_data.append({col: value for col, value in zip(cols, row)})

        return row_data

    @property
    def rowId(self) -> str:
        return f"params.data.{self.banana_table.primary_key.name}"

    @property
    def tableTitle(self) -> str:
        return self.banana_table.display_name

    @property
    def defaultColDef(self):
        return self.banana_table.defaultColDef

    @property
    def gridOptions(self):
        return self.banana_table.gridOptions
