import unittest

from core.router_files import (
    detect_append_file,
    detect_copy_file,
    detect_create_file,
    detect_create_folder,
    detect_delete_file,
    detect_list_files,
    detect_move_file,
    detect_read_file,
    detect_rename_file,
    detect_write_file,
)


class RouterFilesTests(unittest.TestCase):
    def test_create_file(self):
        self.assertEqual(detect_create_file("crie arquivo teste.txt"), {"intent": "create_file", "target": "teste.txt"})

    def test_write_file_with_content(self):
        self.assertEqual(
            detect_write_file("escreva no arquivo teste.txt: oi"),
            {"intent": "write_file", "target": "teste.txt", "content": "oi"},
        )

    def test_append_file_with_content(self):
        self.assertEqual(
            detect_append_file("adicione no arquivo teste.txt: linha nova"),
            {"intent": "append_file", "target": "teste.txt", "content": "linha nova"},
        )

    def test_read_file(self):
        self.assertEqual(detect_read_file("leia arquivo teste.txt"), {"intent": "read_file", "target": "teste.txt"})

    def test_delete_file(self):
        self.assertEqual(detect_delete_file("apague teste.txt"), {"intent": "delete_file", "target": "teste.txt"})

    def test_delete_file_ignores_watchlist_command(self):
        self.assertIsNone(detect_delete_file("remova BBAS3 da watchlist"))

    def test_copy_file(self):
        self.assertEqual(
            detect_copy_file("copie a.txt para b.txt"),
            {"intent": "copy_file", "target": {"src": "a.txt", "dst": "b.txt"}},
        )

    def test_move_file(self):
        self.assertEqual(
            detect_move_file("mova a.txt para pasta/a.txt"),
            {"intent": "move_file", "target": {"src": "a.txt", "dst": "pasta/a.txt"}},
        )

    def test_rename_file(self):
        self.assertEqual(
            detect_rename_file("renomeie a.txt para b.txt"),
            {"intent": "rename_file", "target": {"src": "a.txt", "new_name": "b.txt"}},
        )

    def test_list_files(self):
        self.assertEqual(detect_list_files("liste arquivos"), {"intent": "list_files", "target": ""})

    def test_create_folder(self):
        self.assertEqual(detect_create_folder("crie pasta relatórios"), {"intent": "create_folder", "target": "relatórios"})


if __name__ == "__main__":
    unittest.main()
