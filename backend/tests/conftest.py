import os
import tempfile

TEST_DATA_DIRECTORY = tempfile.TemporaryDirectory(prefix="organchip-tests-")
os.environ["ORGANCHIP_DATA_DIR"] = TEST_DATA_DIRECTORY.name
