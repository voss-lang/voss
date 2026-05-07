from importlib import resources


def test_voss_py_typed_marker_available():
    assert resources.files("voss").joinpath("py.typed").is_file()
