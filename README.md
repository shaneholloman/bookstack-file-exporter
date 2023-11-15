# bookstack-file-exporter
## Background
_Features are actively being developed. See `Future Items` section for more details. Open an issue for a feature request._

This tool provides a way to export Bookstack pages in a folder-tree layout locally with an option to push to remote object storage locations. See `Backup Behavior` section for more details on how pages are organized.

This small project was mainly created to run as a cron job in k8s but works anywhere. This tool allows me to export my docs in markdown, or other formats like pdf. I use Bookstack's markdown editor as default instead of WYSIWYG editor and this makes my notes portable anywhere even if offline.

The main use case is to backup all docs in a folder-tree format to cover the scenarios:

1. Offline copy wanted.
2. Back up at a file level as an accessory or alternative to disk and volume backups.
3. Share docs with another person to keep locally.
4. Migrate to Markdown documenting for simplicity.
5. Provide an easy way to do automated file backups locally, in docker, or kubernetes.

Supported backup targets are:

1. local
2. minio
3. s3 (Not Yet Implemented)

Supported backup formats are shown [here](https://demo.bookstackapp.com/api/docs#pages-exportHtml) and below:

1. html
2. pdf
3. markdown
4. plaintext

Backups are exported in `.tgz` format and generated based off timestamp. Export names will be in the format: `%Y-%m-%d_%H-%M-%S` (Year-Month-Day_Hour-Minute-Second). *Files are first pulled locally to create the tarball and then can be sent to object storage if needed*. Example file name: `bookstack_export_2023-09-22_07-19-54.tgz`.

The exporter can also do housekeeping duties and keep a configured number of archives and delete older ones. See `keep_last` property in the `Configuration` section. Object storage provider configurations include their own `keep_last` property for flexibility. 

## Using This Application
Ensure a valid configuration is provided when running this application. See `Configuration` section for more details.

### Run via Pip
```bash
python -m pip install bookstack-file-exporter

# if you already have python bin directory in your path
bookstack-file-exporter -c <path_to_config_file>

# using pip
python -m bookstack_file_exporter -c <path_to_config_file>
```
Command line options:
| option | required | description |
| ------ | -------- | ----------- |
|`-c`, `--config-file`|True|Relative or Absolute path to a valid configuration file. This configuration file is checked against a schema for validation.|
|`-v`, `--log-level` |False, default: info|Provide a valid log level: info, debug, warning, error.|

_Note: This application is tested and developed on Python `3.11.X`. It will probably work for >= `3.8` but is recommended to install (or set up a venv) a `3.11.X` version._

### Run Via Docker
Example:

```bash
docker run \
    --user ${USER_ID}:${USER_GID} \
    -v $(pwd)/config.yml:/export/config/config.yml:ro \
    -v $(pwd)/bkps:/export/dump \
    homeylab/bookstack-file-exporter:latest
```
Minimal example with object storage upload: 
```bash
docker run \
    -v $(pwd)/config.yml:/export/config/config.yml:ro \
    homeylab/bookstack-file-exporter:latest
```

Tokens and other options can be specified, example:
```bash
# '-e' flag for env vars
# --user flag to override the uid/gid for created files
docker run \
    -e LOG_LEVEL='debug' \
    -e BOOKSTACK_TOKEN_ID='xyz' \
    -e BOOKSTACK_TOKEN_SECRET='xyz' \
    --user 1000:1000 \
    -v $(pwd)/config.yml:/export/config/config.yml:ro \
    -v $(pwd)/bkps:/export/dump \
    homeylab/bookstack-file-exporter:latest
```
Bind Mounts:
| purpose | static docker path | description | example |
| ------- | ------------------ | ----------- | ------- |
| `config` | `/export/config/config.yml` | A valid configuration file |`-v /local/yourpath/config.yml:/export/config/config.yml:ro`|
| `dump` | `/export/dump` | Directory to place exports. **This is optional when using remote storage option(s)**. Omit if you don't need a local copy. | `-v /local/yourpath/bkps:/export/dump` |

### Authentication
**Note visibility of pages is based on user**, so use a user that has access to pages you want to back up.

Ref: [https://demo.bookstackapp.com/api/docs#authentication](https://demo.bookstackapp.com/api/docs#authentication)

Provide a tokenId and a tokenSecret as environment variables or directly in the configuration file.
- `BOOKSTACK_TOKEN_ID`
- `BOOKSTACK_TOKEN_SECRET`

Env variables for credentials will take precedence over configuration file options if both are set.

**For object storage authentication**, find the relevant sections further down in their respective sections.

### Configuration
See below for an example and explanation. Optionally, look at `examples/` folder of the github repo for more examples. 

For object storage configuration, find more information in their respective sections
- [Minio](https://github.com/homeylab/bookstack-file-exporter#minio-backups)

Schema and values are checked so ensure proper settings are provided. As mentioned, credentials can be specified as environment variables instead if preferred.
```yaml
# if http/https not specified, defaults to https
# if you put http here, it will try verify=false, to not check certs
host: "https://bookstack.yourdomain.com"

# You could optionally set the bookstack token_id and token_secret here instead of env
# If env variable is also supplied, env variable will take precedence
credentials:
    token_id: ""
    token_secret: ""

# additional headers to add, examples below
additional_headers:
  test: "test"
  test2: "test2"
  User-Agent: "test-agent"

# supported formats from bookstack below
# valid formats: markdown, html, pdf, plaintext
# you can specify one or as many as you'd like
formats:
  - markdown
  - html
  - pdf
  - plaintext

# optional minio configuration
# If not required, you should omit/comment out the section
# You can specify env vars instead for access and secret key
# See Minio Backups section of this doc for more info on required fields
minio_config:
  host: "minio.yourdomain.com"
  access_key: ""
  secret_key: ""
  region: "us-east-1"
  bucket: "mybucket"
  path: "bookstack/file_backups"
  keep_last: 5

# output directory for the exported archive
# relative or full path
# User who runs the command should have access to write and create sub folders in this directory
# optional, if not provided, will use current run directory by default
output_path: "bkps/"

# optional export of metadata about the page in a json file
# this metadata contains general information about the page
# like: last update, owner, revision count, etc.
# omit this or set to false if not needed
export_meta: true

# optional if specified exporter can delete older archives
# valid values are:
# set to -1 if you want to delete all archives after each run
# - this is useful if you only want to upload to object storage
# set to 1+ if you want to retain a certain number of archives
# set to 0 or comment out section if you want no action done
keep_last: 5
```

### Backup Behavior
We will use slug names (from Bookstack API) by default, as such certain characters like `!`, `/` will be ignored and spaces replaced.

All sub directories will be created as required during the export process.

```
Shelves --> Books --> Chapters --> Pages

## Example
kafka
---> controller
    ---> settings
        ---> logs (chapter)
            ---> retention.md
            ---> compression.pdf
            ---> something.html
            ---> other.txt
        ---> optional
        ---> main
    ---> deploy
---> broker
    ---> settings
    ---> deploy
---> schema-registry
    ---> protobuf
    ---> settings
```

Books without a shelf will be put in a shelve folder named `unassigned`.

Empty/New Pages will be ignored since they have not been modified yet from creation and are empty but also do not have a valid slug. Example:
```
{
    ...
    "name": "New Page",
    "slug": "",
    ...
}
```

You may notice some directories (books) and/or files (pages) in the archive have a random string at the end, example - `nKA`: `user-and-group-management-nKA`. This is expected and is because there were resources with the same name created in another shelve and bookstack adds a string at the end to ensure uniqueness.

### Minio Backups
Optionally, look at `examples/` folder of the github repo for more examples. 

```yaml
minio_config:
    # a host/ip + port combination is also allowed
    # example: "minio.yourdomain.com:8443"
    host: "minio.yourdomain.com"

    # this is required since minio api appears to require it
    # set to the region your bucket resides in
    # if unsure, try "us-east-1" first
    region: "us-east-1"

    # bucket to upload to
    bucket "mybucket"

    # access key for the minio instance
    # optionally set as env variable instead
    access_key: ""

    # secret key for the minio instance
    # optionally set as env variable instead
    secret_key: ""

    # the path of the backup
    # optional, will use root bucket path if not set
    # in example below, the exported archive will appear in: `<bucket_name>:/bookstack/backups/bookstack-<timestamp>.tgz`
    path: "bookstack/file_backups"

    # optional if specified exporter can delete older archives
    # valid values are:
    # set to 1+ if you want to retain a certain number of archives
    # set to 0 or comment out section if you want no action done
    keep_last: 5
```

As mentioned you can optionally set access and secret key as env variables. If both are specified, env variable will take precedence.
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`

## Future Items
1. Be able to pull media/photos locally and place in their respective page folders for a more complete file level backup.
2. Include the exporter in a maintained helm chart as an optional deployment. The helm chart is [here](https://github.com/homeylab/helm-charts/tree/main/charts/bookstack).
3. Export S3 or more options.
4. Filter shelves and books by name - for more targeted backups. Example: you only want to share a book about one topic with an external friend/user.
5. Be able to pull media/photos from 3rd party providers like `drawio`