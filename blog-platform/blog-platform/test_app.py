import os, tempfile, unittest
import app as blog

class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        blog.app.config.update(DATABASE=os.path.join(self.tmp, "t.db"), TESTING=True)
        self.c = blog.app.test_client()
        with self.c.session_transaction() as s:
            s["_csrf"] = "tok"

    def post(self, url, **data):
        with self.c.session_transaction() as s:   # login/logout clear the session
            s["_csrf"] = "tok"
        data["_csrf"] = "tok"
        return self.c.post(url, data=data, follow_redirects=True)

    def login_demo(self):
        return self.post("/login", username="demo", password="demo1234")

    def test_home_and_seed(self):
        r = self.c.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Welcome to Inkwell", r.data)

    def test_csrf_blocked(self):
        r = self.c.post("/login", data={"username": "demo", "password": "demo1234"})
        self.assertEqual(r.status_code, 400)

    def test_register_login_logout(self):
        r = self.post("/register", username="alice", password="secret1")
        self.assertIn(b"Welcome to Inkwell, alice", r.data)
        self.post("/logout")
        r = self.post("/login", username="alice", password="wrong")
        self.assertIn(b"Wrong username or password", r.data)
        r = self.post("/login", username="alice", password="secret1")
        self.assertIn(b"Welcome back", r.data)
        r = self.post("/register", username="alice", password="secret1")  # logged in -> redirect
        self.assertEqual(r.status_code, 200)

    def test_duplicate_and_invalid_register(self):
        r = self.post("/register", username="demo", password="secret1")
        self.assertIn(b"already taken", r.data)
        r = self.post("/register", username="a!", password="secret1")
        self.assertIn(b"3-20 characters", r.data)

    def test_post_lifecycle_and_xss(self):
        self.login_demo()
        r = self.post("/new", title="<b>Hi</b>", tags="Python, Web Dev, python",
                      content="Hello **world** <script>alert(1)</script> [x](javascript:alert(2))")
        self.assertIn(b"Your post is live", r.data)
        self.assertNotIn(b"<script>alert", r.data)
        self.assertNotIn(b"javascript:alert", r.data)
        self.assertIn(b"&lt;b&gt;Hi&lt;/b&gt;", r.data)
        self.assertIn(b"#web-dev", r.data)
        r = self.c.get("/?q=world")
        self.assertIn(b"1 result", r.data)
        r = self.c.get("/?tag=web-dev")
        self.assertIn(b"1 result", r.data)

    def test_edit_delete_permissions(self):
        self.login_demo()
        self.post("/new", title="Mine", content="Some content here, enough text.")
        self.post("/logout")
        self.post("/register", username="bob", password="secret1")
        self.assertEqual(self.c.get("/post/1/edit").status_code, 403)
        r = self.post("/post/1/delete")
        self.assertEqual(r.status_code, 403)

    def test_like_and_comment(self):
        self.login_demo()
        r = self.post("/post/1/like")
        self.assertIn(b"Liked", r.data)
        r = self.post("/post/1/like")
        self.assertNotIn(b"Liked &middot;", r.data)
        r = self.post("/post/1/comment", body="Nice read!")
        self.assertIn(b"Nice read!", r.data)
        r = self.post("/post/1/comment", body="   ")
        self.assertIn(b"between 1 and 1000", r.data)

    def test_edit_and_delete_own(self):
        self.login_demo()
        r = self.post("/post/1/edit", title="Changed title", tags="x", content="Updated content body here.")
        self.assertIn(b"Post updated", r.data)
        self.assertIn(b"Changed title", r.data)
        r = self.post("/post/1/delete")
        self.assertIn(b"Post deleted", r.data)
        self.assertEqual(self.c.get("/post/1").status_code, 404)

    def test_pages_and_errors(self):
        self.assertEqual(self.c.get("/u/demo").status_code, 200)
        self.assertEqual(self.c.get("/u/nobody").status_code, 404)
        self.assertEqual(self.c.get("/new", follow_redirects=False).status_code, 302)
        self.assertEqual(self.c.get("/?page=999").status_code, 200)
        self.login_demo()
        with self.c.session_transaction() as s:
            s["_csrf"] = "tok"
        r = self.c.post("/preview", data={"_csrf": "tok", "content": "# Hi"})
        self.assertIn("<h1>Hi</h1>", r.get_json()["html"])

if __name__ == "__main__":
    unittest.main()
