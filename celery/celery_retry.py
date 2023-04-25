# note:
# @app.task(autoretry_for=(FailWhaleError,) retry_backoff=True)
# @app.task(autoretry_for=(FailWhaleError,) retry_kwargs={'max_retries': 5,'countdown':10})
# @app.task(on_failure=exception_handle, on_retry=retry_handle, bind=True)
# def taskname(self, chainid, hash, type, name, amount):
#     try:
#         raise
#     except BaseException as e:
#         raise self.retry(exc=e, max_retries=360, countdown=10)
#
# def retry_handle(self, exc, task_id, args, kwargs, einfo):
#     loggert.exception(exc)
