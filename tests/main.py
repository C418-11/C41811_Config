# -*- coding: utf-8 -*-


from collections import OrderedDict
from collections.abc import Mapping
from copy import deepcopy
from typing import MutableMapping
from unittest import TestCase
from unittest import main

from pydantic import BaseModel, Field

from src.C41811.Config import ConfigData
from src.C41811.Config import RequiredKey
from src.C41811.Config.errors import ConfigDataTypeError
from src.C41811.Config.errors import RequiredKeyNotFoundError


class ReadOnlyMapping(Mapping):
    def __init__(self, dictionary: MutableMapping):
        self._data = dictionary

    def __getitem__(self, __key):
        return self._data[__key]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)


class TestConfigData(TestCase):
    def setUp(self):
        self.raw_data: OrderedDict = OrderedDict((
            ("foo", OrderedDict((
                ("bar", 123),
            ))),
            ("foo1", 114),
            ("foo2", ["bar"])
        ))

    def test_init(self):
        data = ConfigData(self.raw_data)
        data["foo.bar"] = 456
        self.assertNotEqual(self.raw_data, data.data)

    def test_getattr(self):
        self.assertEqual(ConfigData(self.raw_data)["foo.bar"], 123)

    def test_setattr(self):
        data = ConfigData(self.raw_data)
        data["foo.bar"] = 456
        self.assertEqual(data["foo.bar"], 456)
        data["foo3.bar"] = 789
        self.assertEqual(data["foo3.bar"], 789)
        with self.assertRaises(RequiredKeyNotFoundError):
            data.setPathValue("foo3.bar1", 789, allow_create=False)
        self.assertNotIn("foo3.bar1", data)

    def test_delattr(self):
        data = ConfigData(self.raw_data)
        del data["foo.bar"]
        self.assertNotIn("foo.bar", data)

    def test_readonly_attr(self):
        data = ConfigData(self.raw_data)
        self.assertFalse(data.read_only)
        readonly = ConfigData(ReadOnlyMapping(self.raw_data))
        self.assertTrue(readonly.read_only)

    def test_data_attr(self):
        data = ConfigData(self.raw_data)
        last_data = data.data
        data["foo.bar"] = 456
        self.assertNotEqual(last_data, data.data)

        with self.assertRaises(AttributeError):
            # noinspection PyPropertyAccess
            data.data = {}

    def test_readonly_getattr(self):
        data = ConfigData(ReadOnlyMapping(self.raw_data))
        self.assertEqual(data["foo.bar"], 123)

        data = ConfigData(self.raw_data)
        data.read_only = True
        with self.assertRaisesRegex(TypeError, r"read-only"):
            data["foo.bar"] = 456

        self.assertEqual(data["foo.bar"], 123)

    def test_readonly_setattr(self):
        data = ConfigData(ReadOnlyMapping(self.raw_data))

        with self.assertRaisesRegex(TypeError, r"read-only"):
            data["foo.bar"] = 456

        self.assertEqual(data["foo.bar"], 123)

    def test_readonly_delattr(self):
        data = ConfigData(ReadOnlyMapping(self.raw_data))

        with self.assertRaisesRegex(TypeError, r"read-only"):
            del data["foo.bar"]

        self.assertIn("foo.bar", data)

    def test_config_data_type_error(self):
        data = ConfigData(self.raw_data)

        with self.assertRaises(ConfigDataTypeError):
            data.getPathValue("foo1.bar")
        with self.assertRaises(ConfigDataTypeError):
            data.setPathValue("foo1.bar", 456)
        with self.assertRaises(ConfigDataTypeError):
            data.deletePath("foo1.bar")

        readonly_data = deepcopy(self.raw_data)
        readonly_data["foo"] = ReadOnlyMapping(readonly_data["foo"])
        readonly = ConfigData(readonly_data)
        with self.assertRaises(ConfigDataTypeError):
            readonly.setPathValue("foo.bar", 456)
        self.assertEqual(readonly.getPathValue("foo.bar"), 123)
        with self.assertRaises(ConfigDataTypeError):
            readonly.deletePath("foo.bar")
        self.assertEqual(readonly.getPathValue("foo.bar"), 123)

    def test_required_key_not_found_error(self):
        data = ConfigData(self.raw_data)

        with self.assertRaises(RequiredKeyNotFoundError):
            data.getPathValue("foo3")
        with self.assertRaises(RequiredKeyNotFoundError):
            data.setPathValue("foo3", 456, allow_create=False)
        with self.assertRaises(RequiredKeyNotFoundError):
            data.deletePath("foo3")

    def test_get(self):
        data = ConfigData(self.raw_data)
        self.assertEqual(data.get("foo.bar"), 123)
        self.assertIsNone(data.get("not exist"))
        self.assertEqual(data.get("not exist", 456), 456)

    def test_set_default(self):
        data = ConfigData(self.raw_data)
        self.assertEqual(data.set_default("foo.bar", 123), 123)
        self.assertIsNone(data.set_default("not_exist"))
        self.assertIn("not_exist", data)
        self.assertEqual(data.set_default("not_exist1", {"bar": 456}), {"bar": 456})
        self.assertIn("not_exist1.bar", data)
        self.assertEqual(data["not_exist1.bar"], 456)

    def test_contains(self):
        data = ConfigData(self.raw_data)
        self.assertIn("foo", data)
        self.assertIn("foo.bar", data)

    def test_eq(self):
        data = ConfigData(self.raw_data)
        readonly = ConfigData(ReadOnlyMapping(self.raw_data))
        self.assertEqual(data, readonly)

    def test_sep_char(self):
        data = ConfigData(self.raw_data)
        self.assertEqual(data.sep_char, '.')
        data = ConfigData(self.raw_data, sep_char='$')
        self.assertEqual(data.sep_char, '$')
        self.assertEqual(data["foo$bar"], 123)

        with self.assertRaises(AttributeError):
            # noinspection PyPropertyAccess
            data.sep_char = '.'

    def test_deepcopy(self):
        data = ConfigData(self.raw_data)
        last_data = deepcopy(data)
        data["foo.bar"] = 456
        self.assertNotEqual(last_data, data)

    def test_keys(self):
        data = ConfigData(self.raw_data)
        self.assertSetEqual(set(data.keys()), set(self.raw_data.keys()))

    def test_values(self):
        data = ConfigData(self.raw_data)
        values = [ConfigData(v) if isinstance(v, Mapping) else v for v in self.raw_data.values()]
        self.assertSequenceEqual(list(data.values()), values)

    def test_items(self):
        data = ConfigData(self.raw_data)
        data_items = tuple((k, v) for k, v in data.items())
        items = tuple((k, ConfigData(v)) if isinstance(v, Mapping) else (k, v) for k, v in self.raw_data.items())
        self.assertTupleEqual(data_items, items)


class TestRequiredKey(TestCase):
    def setUp(self):
        self.data = ConfigData({
            "foo": {
                "bar": 123
            },
            "foo1": 114,
            "foo2": ["bar"]
        })

    def test_build_cache(self):
        # 提前执行一次让pydantic提前导入所需的模块，让后续测试的运行时间更有参考性
        # noinspection PyBroadException
        try:
            self.test_pydantic()
            self.test_default_iterable()
            self.test_default_mapping()
        except Exception:
            pass
        self.skipTest("让pydantic提前导入所需的模块，让后续测试的运行时间更有参考性")

    def test_pydantic(self):
        class Foo(BaseModel):
            bar: int = Field(123)
            bar1: int = Field(456)

        class Data(BaseModel):
            foo: Foo = Field(default_factory=Foo)
            foo1: int
            foo2: list[str]

        data = RequiredKey(Data, "pydantic").filter(self.data)

        self.assertIn("foo.bar", data)
        self.assertEqual(data["foo.bar"], 123)
        self.assertIn("foo.bar1", data)
        self.assertEqual(data["foo.bar1"], 456)

    def test_pydantic_with_error(self):
        class NotExist(BaseModel):
            foo3: int

        with self.assertRaises(RequiredKeyNotFoundError):
            RequiredKey(NotExist, "pydantic").filter(self.data)

        class NotExist2(BaseModel):
            foo: NotExist

        with self.assertRaises(RequiredKeyNotFoundError):
            RequiredKey(NotExist2, "pydantic").filter(self.data)

        class WrongType(BaseModel):
            foo: str

        with self.assertRaises(ConfigDataTypeError):
            RequiredKey(WrongType, "pydantic").filter(self.data)

        class WrongType2(BaseModel):
            foo2: list[int]

        with self.assertRaises(ConfigDataTypeError):
            RequiredKey(WrongType2, "pydantic").filter(self.data)

    def test_default_iterable(self):
        data = RequiredKey([
            "foo.bar",
            "foo1",
            "foo2",
        ]).filter(self.data)

        self.assertIn("foo.bar", data)
        self.assertEqual(data["foo.bar"], 123)
        self.assertEqual(data["foo1"], 114)
        self.assertEqual(data["foo2"], ["bar"])

    def test_default_iterable_with_error(self):
        with self.assertRaises(RequiredKeyNotFoundError):
            RequiredKey(["foo.bar1"]).filter(self.data, allow_create=True)
        with self.assertRaises(ConfigDataTypeError):
            RequiredKey(["foo.bar.err_type"]).filter(self.data, allow_create=True)

    def test_default_mapping(self):
        data = RequiredKey({
            "foo.bar": int,
            "foo1": int,
            "foo2": list[str],
        }).filter(self.data)

        self.assertIn("foo.bar", data)
        self.assertEqual(data["foo.bar"], 123)
        self.assertEqual(data["foo1"], 114)
        self.assertSequenceEqual(data["foo2"], ["bar"])

        data = RequiredKey({
            "foo.bar": int,
            "foo1": int,
            "foo2": list[str],
            "foo.bar1.test": 456,
        }).filter(self.data, allow_create=True)

        self.assertEqual(data["foo.bar"], 123)
        self.assertEqual(data["foo1"], 114)
        self.assertSequenceEqual(data["foo2"], ["bar"])
        self.assertIn("foo.bar1.test", data)
        self.assertEqual(data["foo.bar1.test"], 456)

    def test_default_mapping_with_error(self):
        with self.assertRaises(RequiredKeyNotFoundError):
            RequiredKey({
                "foo3": int
            }).filter(self.data)

        with self.assertRaises(ConfigDataTypeError):
            RequiredKey({
                "foo.bar": str,
            }).filter(self.data)

        with self.assertRaises(ConfigDataTypeError):
            RequiredKey({
                "foo.bar": str,
            }).filter(self.data, allow_create=True)

        with self.assertRaises(ConfigDataTypeError):
            RequiredKey({
                "foo2": list[int]
            }).filter(self.data)

        with self.assertRaises(ConfigDataTypeError):
            RequiredKey({
                "foo2": list[int]
            }).filter(self.data, allow_create=True)


if __name__ == "__main__":
    main()
