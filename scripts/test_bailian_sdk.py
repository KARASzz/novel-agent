import inspect
from alibabacloud_bailian20231229 import models

print("AddFileRequest:", inspect.signature(models.AddFileRequest.__init__))
print("SubmitIndexAddDocumentsJobRequest:", inspect.signature(models.SubmitIndexAddDocumentsJobRequest.__init__))
try:
    print("SubmitIndexJobRequest:", inspect.signature(models.SubmitIndexJobRequest.__init__))
except: pass
