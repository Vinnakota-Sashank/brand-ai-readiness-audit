#!/usr/bin/env python3
import json
import os
import sys


def validate_type(instance, schema, path="root"):
    expected_type = schema.get("type")
    if expected_type:
        type_list = expected_type if isinstance(expected_type, list) else [expected_type]
        type_map = {
            "object": dict,
            "array": list,
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "null": type(None),
        }
        valid = False
        for t in type_list:
            if t in type_map and isinstance(instance, type_map[t]):
                if t == "integer" and type(instance) is bool:
                    continue  # bool is a subclass of int, but we want strict checking
                valid = True
                break

        if not valid:
            return f"{path}: Expected {type_list}, got {type(instance).__name__}"

        if "string" in type_list and isinstance(instance, str) and schema.get("format") == "date-time":
            import datetime

            try:
                dt_str = instance.replace("Z", "+00:00")
                datetime.datetime.fromisoformat(dt_str)
            except ValueError:
                return f"{path}: '{instance}' is not a valid ISO 8601 date-time string"

    if "minimum" in schema and isinstance(instance, (int, float)) and instance < schema["minimum"]:
        return f"{path}: Value {instance} is less than minimum {schema['minimum']}"

    if "maximum" in schema and isinstance(instance, (int, float)) and instance > schema["maximum"]:
        return f"{path}: Value {instance} is greater than maximum {schema['maximum']}"

    if "enum" in schema and instance not in schema["enum"]:
        return f"{path}: Value {instance!r} not in allowed enum {schema['enum']}"

    if "minLength" in schema and isinstance(instance, str) and len(instance) < schema["minLength"]:
        return f"{path}: String too short, expected at least {schema['minLength']} chars"

    if "pattern" in schema and isinstance(instance, str):
        import re

        if not re.search(schema["pattern"], instance):
            return f"{path}: String '{instance}' does not match pattern '{schema['pattern']}'"

    if isinstance(instance, dict):
        if "required" in schema:
            for req in schema["required"]:
                if req not in instance:
                    return f"{path}: Missing required property '{req}'"

        for k, v in instance.items():
            if "properties" in schema and k in schema["properties"]:
                err = validate_type(v, schema["properties"][k], path=f"{path}.{k}")
                if err:
                    return err
            elif schema.get("additionalProperties") is False:
                return f"{path}: Additional property '{k}' not allowed"

    elif isinstance(instance, list):
        if "items" in schema:
            for i, item in enumerate(instance):
                err = validate_type(item, schema["items"], path=f"{path}[{i}]")
                if err:
                    return err

    return None


def main():
    if len(sys.argv) > 1 and sys.argv[1] != "-":
        filepath = sys.argv[1]
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}", file=sys.stderr)
            sys.exit(2)
        with open(filepath, "r", encoding="utf-8") as f:
            data = f.read()
    else:
        data = sys.stdin.read()

    if not data.strip():
        print(
            "Usage: python3 validate_report.py [report.json | - < report.json]",
            file=sys.stderr,
        )
        sys.exit(2)

    try:
        report = json.loads(data)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(2)

    schema_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references", "report-schema.json"
    )
    if not os.path.exists(schema_path):
        print(f"Schema not found at {schema_path}", file=sys.stderr)
        sys.exit(2)

    with open(schema_path, "r") as f:
        schema = json.load(f)

    err = validate_type(report, schema)
    if err:
        print(f"Schema validation failed: {err}", file=sys.stderr)
        sys.exit(2)

    print(json.dumps(report, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
