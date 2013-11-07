import mock

session = mock.Mock()
uid = 1

session.execute("SELECT foo FROM bar")
session.execute("SELECT foo FROM bar WHERE id=%s", uid)
