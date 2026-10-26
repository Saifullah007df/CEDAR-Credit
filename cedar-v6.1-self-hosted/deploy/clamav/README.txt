For production file uploads, provide approved offline ClamAV signature databases
(.cvd/.cld) in this folder before starting the service. Keep them updated via an
approved offline process. Without signatures, clamscan fails closed and document
uploads are rejected, rather than being accepted unscanned.
