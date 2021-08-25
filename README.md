# httpserver-python
Extension of SimpleHTTPServer for chunked transfer encoding and compressed content encoding


## Usage

Run the httpserver.py from a terminal in the location where it should be serving files and other content:

```
  $ > ./httpserver.py
```

The server supports the following options:

|Short|Long                | Documentation                                                                     |
|-----|--------------------|-----------------------------------------------------------------------------------|
|--ce |--content-encoding  | Content encoding type for server to utilize (gzip, deflate or zip). Default: gzip |
|--te |--transfer-encoding | Transfer encoding type for server to utilize (chunked). Default: none             |
|-p   |--port              | The port to serve the files on. Default: 8000                                     |

## Request methods

The server supports the following request methods:

|Method|                                                                 |
|------|-----------------------------------------------------------------|
| GET  | Download requested resource or return a default file index.html |
| PUT  | Store the resource in the request body as a file                |
| HEAD | Return response header but no response body                     |
