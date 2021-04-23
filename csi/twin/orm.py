import collections
import collections.abc
import re
import sqlite3
from pathlib import Path
from typing import Any, Generator, List, MutableMapping, Tuple, Union

from csi.transform import json_transform, json_parse

structural_fields = {
    "id",
    "parent_id",
}
message_fields = {"entity_id", "unix_toi", "label"}
scalar_fields = {
    "data",
}


class DataTable:
    def __init__(self, db, table_name):
        self.db = db
        self.table_name = table_name.lower()
        # Retrieve all column names
        tbl_info_query = "PRAGMA table_info('{}')"
        columns = db.connection.execute(
            tbl_info_query.format(self.table_name)
        ).fetchall()
        self.column_names = [n for (_, n, t, _, _, _) in columns]
        # Retrieve foreign keys constraints
        fk_info_query = "PRAGMA foreign_key_list('{}')"
        foreign_keys = db.connection.execute(
            fk_info_query.format(self.table_name)
        ).fetchall()
        self.foreign_keys = {
            field: (fk_table.lower(), fk_name)
            for _, _, fk_table, field, fk_name, _, _, _ in foreign_keys
        }
        # Retrieve primary key columns
        self.primary_keys = [n for (_, n, _, _, _, p) in columns if p == 1]
        assert self.primary_keys
        #
        self._query_all = None

    @property
    def query_all(self):
        if self._query_all is None:
            self._query_all = SelectionQuery(self)
        return self._query_all

    def is_structural(self):
        return len(structural_fields - set(self.column_names)) == 0

    def all(self, filter=""):
        yield from self.query_all.execute(filter)

    def messages(self):
        if self.is_structural():
            yield from self.all("{}.parent_id == 'NULL'".format(self.table_name))


class SelectionQuery:
    def __init__(self, table: DataTable):
        self.table = table
        self.fields = self.compute_query_fields()
        self.clauses = self.compute_query_clauses()

    def compute_query_fields(self) -> List[Tuple[bool, Tuple, List[Tuple[str, str]]]]:
        """Prepare a list of fields selected by the query, with metadata.

        Each field is provided with:
        - a boolean to indicate if it is a primary key
        - a tuple of list of fields table by table traversed to reach the described one
        - a list of corresponding traversed foreign table and linked foreign fields

        The `n`th value in the field list belongs to the `n-1` table and is linked to the `n`th table on the `n`th
        foreign key. As an example, `(True, ('label', 'id'), [('String', 'parent_id')])` describes the path to the `id`
        field of the `String` table. The current table `label` field is linked to table `String` on field `parent_id`.
        """
        fields = []
        # First query for the table primary keys
        for primary_key in self.table.primary_keys:
            fields.append((True, (primary_key,), []))
        # Add remaining fields, including foreign values
        for field in self.table.column_names:
            if field in self.table.foreign_keys:
                # Add fields from linked table for foreign key
                fk_table, fk_field = self.table.foreign_keys[field]
                for is_pk, field_path, field_tables in SelectionQuery(
                    self.table.db.tables[self.table.foreign_keys[field][0]]
                ).fields:
                    # Skip foreign structural fields except primary keys
                    if (
                        field_path[-1] not in (structural_fields | message_fields)
                        or is_pk
                    ):
                        fields.append(
                            (
                                is_pk,
                                (field,) + field_path,
                                [(fk_table, fk_field)] + field_tables,
                            )
                        )
            else:
                fields.append((False, (field,), []))
        return fields

    def compute_query_clauses(self):
        """Prepare select and join clauses to get the nest table contents."""
        joins = []
        selects = []
        # Iterate over all required fields
        for (_, path, tables) in self.fields:
            # Create foreign table alias for foreign keys
            if not tables:
                table_alias = self.table.table_name
            else:
                table_alias = (
                    "fk_" + "_".join(path[:-1])
                    if len(path) > 1
                    else self.table.table_name
                )
            # Select current field
            selects.append("{}.{}".format(table_alias, path[-1]))
            # Create join clauses for foreign keys
            fk_a = "fk"
            current = self.table.table_name
            # Iterate over foreign key constraints and tables
            for fk_s, (fk_t, fk_f) in zip(path, tables):
                fk_a += "_" + fk_s
                j = "LEFT JOIN {} {} ON {}.{} = {}.{}".format(
                    fk_t, fk_a, current, fk_s, fk_a, fk_f
                )
                if j not in joins:
                    joins.append(j)
                current = fk_a
        return joins, selects

    def prepare(self, filter=""):
        joins, selects = self.clauses
        query = "SELECT {}\nFROM {} {}".format(
            ",\n".join(selects), self.table.table_name, "\n".join(joins)
        )
        # Define query template
        if filter:
            query += " WHERE {}".format(filter)
        return query

    def initialise_element(self):
        return {"__table__": self.table.table_name}

    def execute(self, filter=""):
        # Current element contents/id
        element = self.initialise_element()
        element_id = None
        encountered_pks = collections.defaultdict(set)
        # Process each query row
        for row in self.table.db.connection.execute(self.prepare(filter)).fetchall():
            # Current row primary key for foreign tables, and current one
            row_pk = {}
            row_id = []
            # Match row contents with selected fields' metadata
            for (is_pk, field_path, field_tables), field_value in zip(self.fields, row):
                if is_pk:
                    # Get current row id and foreign pk
                    assert field_path[:-1] not in row_pk
                    row_pk[field_path[:-1]] = field_value
                    if not field_tables:
                        row_id.append(field_value)
                else:
                    # Start of new element, yield current one
                    if element_id != row_id:
                        if element_id is not None:
                            yield element
                            element = self.initialise_element()
                        element_id = row_id
                    # Skip unresolved foreign keys
                    if row_pk[field_path[:-1]] is None:
                        continue
                    # Skip fields which value has been inserted
                    if row_pk[field_path[:-1]] in encountered_pks[field_path]:
                        continue
                    # Navigate to value position, defined by traversed pk and field for each foreign field
                    value_position = element
                    for i in range(len(field_path) - 1):
                        # Retrieve field in foreign table and descend in element structure
                        field = field_path[i]
                        if field not in value_position:
                            value_position[field] = dict()
                        value_position = value_position[field]
                    # Insert value if not present
                    # assert value_position.get(field_path[-1], field_value) == field_value, "Value at {} ({}) differs from current ({})".format(field_path, field_value, value_position.get(field_path[-1]))
                    if field_path[-1] in value_position:
                        if not isinstance(value_position[field_path[-1]], list):
                            t = value_position[field_path[-1]]
                            value_position[field_path[-1]] = list()
                            value_position[field_path[-1]].append(t)
                        value_position[field_path[-1]].append(field_value)
                    else:
                        value_position[field_path[-1]] = field_value
                    # Record current element as inserted
                    encountered_pks[field_path].add(row_pk[field_path[:-1]])
                    # value_position[field_path[-1]] = field_value
                    # Record foreign table and id in meta-data
                    if field_tables:
                        table = field_tables[-1][0]
                        field_pk = row_pk[field_path[:-1]]
                        value_position["__table__"] = table
                        value_position["__pk__"] = field_pk
        # Yield final element
        if element != self.initialise_element():
            yield element


class DataBase:
    path_foreign_index = json_parse("$[*]..[?(@.__table__)]")
    path_foreign_data = json_parse(
        "$..[?(@.length() = 1 and @[0][?(@.__table__ and @.__pk__)])]"
    )
    path_data_table = json_parse("$..[?(@.data and @.keys().length() = 1)]")
    path_snake_case = json_parse("$..[?(@.keys().length() > 0)]")

    def __init__(self, path: Union[str, Path]):
        self.db_path = Path(path)
        self.connection = sqlite3.connect(path)
        # Retrieve the list of tables in the database
        all_tbl_query = "SELECT name FROM sqlite_master WHERE type='table'"
        tables = self.connection.execute(all_tbl_query).fetchall()
        self.tables = {
            t[0].lower(): DataTable(self, t[0])
            for t in tables
            if t[0] not in ["sqlite_sequence"]
        }

    def messages(self, *tables) -> Generator:
        if tables:
            from_tables = [self.tables[t] for t in tables if t in self.tables]
        else:
            from_tables = self.tables.values()
        for table in from_tables:
            yield from table.messages()

    def flatten_messages(self, *tables) -> Generator:
        reduce_fk = lambda c: {
            k: v for k, v in c.items() if k not in ["__table__", "__pk__"]
        }
        snake_case = lambda name: re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
        keys_case = (
            lambda c: {snake_case(k): keys_case(v) for k, v in c.items()}
            if isinstance(c, dict)
            else c
        )
        #
        for message in self.messages(*tables):
            # Remove indexing by foreign table primary id
            message = json_transform(self.path_foreign_index, message, reduce_fk)
            # Flatten foreign tables with a single element
            message = json_transform(self.path_foreign_data, message, lambda d: d[0])
            # Flatten tables containing only data
            message = json_transform(self.path_data_table, message, lambda d: d["data"])
            # Convert terms to snake_case
            message = json_transform(self.path_snake_case, message, keys_case)
            yield message


# TODO Index the database when first accessed to fasten queries -> Compare cost of indexing+query vs. query
# TODO Check if IO or CPU bound by loading database in memory first
# TODO Add immutable and nolock to db uri to increase access speed
