import re


def parse_multipart(environ):

    #print("REQUEST_METHOD:", environ.get("REQUEST_METHOD"))
    #print("TRANSFER_ENCODING:", environ.get("HTTP_TRANSFER_ENCODING"))

    for k, v in environ.items():
        if k.startswith("HTTP_") or k in ("CONTENT_TYPE", "CONTENT_LENGTH"):
            print(k, "=", v)

    content_type = environ.get("CONTENT_TYPE", "")
    content_length = int(environ.get("CONTENT_LENGTH", "0"))

    if "multipart/form-data" not in content_type:
        print("FAIL 111")
        return {}, {}

    m = re.search(r'boundary=(.*)', content_type)

    if not m:
        print("FAIL 222")
        return {}, {}

    boundary = m.group(1).encode()
    body = environ["wsgi.input"].read(content_length)

    print("content_length", content_length)
    print("body length:", len(body))

    parts = body.split(b"--" + boundary)
    fields = {}
    files = {}

    for part in parts:
        part = part.strip()
        if not part or part == b"--":
            continue

        try:
            header_block, content = part.split(b"\r\n\r\n", 1)
        except ValueError:
            continue

        header_lines = header_block.split(b"\r\n")
        headers = {}

        for line in header_lines:
            if b":" in line:
                k, v = line.split(b":", 1)
                headers[k.strip().lower()] = v.strip()

        disp = headers.get(b"content-disposition", b"").decode()
        if "form-data" not in disp:
            continue

        # Extract name="..."
        name_match = re.search(r'name="([^"]+)"', disp)
        if not name_match:
            continue

        field_name = name_match.group(1)

        # Extract filename="..." if present
        filename_match = re.search(r'filename="([^"]+)"', disp)

        if filename_match:
            # This is a file upload
            filename = filename_match.group(1)
            content_type = headers.get(b"content-type", b"application/octet-stream").decode()

            # Strip trailing CRLF + boundary markers
            content = content.rstrip(b"\r\n")

            files[field_name] = {
                "filename": filename,
                "content_type": content_type,
                "content": content,
            }
        else:
            # Normal text field
            value = content.rstrip(b"\r\n").decode(errors="replace")
            fields[field_name] = value

    print("fields", fields)
    print("files", files)

    return fields, files

