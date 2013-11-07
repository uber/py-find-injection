import mock

session = mock.Mock()


session.execute("SELECT foo WHERE id=%s" % 2)
