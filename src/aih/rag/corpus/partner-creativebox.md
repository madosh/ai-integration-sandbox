# CreativeBox Partner Specification

CreativeBox stores creative assets and authenticates with HTTP basic credentials. Creatives are
published with a multipart upload that carries the binary file and a name field. Supported creative
formats are PNG, JPG, and MP4, and the maximum upload size is five megabytes. Uploads accept an
idempotency key derived from the file checksum so that re-uploading identical bytes returns the same
creative id instead of creating a duplicate. Assets can be downloaded again by creative id.
