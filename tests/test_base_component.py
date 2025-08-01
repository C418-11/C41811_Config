from copy import deepcopy
from typing import Any

from pyrsistent import pmap
from pytest import fixture
from pytest import mark
from pytest import raises
from utils import EE
from utils import safe_raises

from c41811.config import ComponentConfigData
from c41811.config import ComponentMember
from c41811.config import ComponentMeta
from c41811.config import ComponentMetaParser
from c41811.config import MappingConfigData
from c41811.config import NoneConfigData
from c41811.config import SequenceConfigData
from c41811.config.abc import ABCIndexedConfigData
from c41811.config.errors import ConfigDataTypeError
from c41811.config.errors import RequiredPathNotFoundError
from c41811.config.utils import Unset

type D_MCD = MappingConfigData[dict[Any, Any]]
type M = dict[str, ABCIndexedConfigData[Any]]
type CCD = ComponentConfigData[ABCIndexedConfigData[dict[Any, Any]], ComponentMeta[D_MCD]]


def _ccd_from_members(members: M) -> CCD:
    return ComponentConfigData(
        meta=ComponentMeta(members=[ComponentMember(fn) for fn in members]),
        members=members,
    )


def _ccd_from_meta(meta: dict[str, Any], members: M) -> CCD:
    return ComponentConfigData(
        ComponentMetaParser().convert_config2meta(MappingConfigData(meta)),
        members,
    )


class TestComponentConfigData:
    @staticmethod
    @fixture
    def empty_data() -> CCD:
        return ComponentConfigData()

    @staticmethod
    @fixture
    def meta() -> ComponentMeta[Any]:
        return ComponentMeta(members=[ComponentMember("foo.json", alias="f"), ComponentMember("bar.json", alias="b")])

    @staticmethod
    @fixture
    def members() -> M:
        return {
            "foo.json": MappingConfigData(
                {
                    "key": {
                        "value": "foo",
                    },
                    "first": {
                        "second": 3,
                    },
                }
            ),
            "bar.json": MappingConfigData({"key": {"value": "bar", "extra": 0}}),
        }

    @staticmethod
    @fixture
    def data(meta: ComponentMeta[D_MCD], members: M) -> CCD:
        return ComponentConfigData(meta, members)

    @staticmethod
    def test_empty_init(empty_data: CCD) -> None:
        assert not empty_data.members
        assert not empty_data.meta.config
        assert not empty_data.meta.members
        assert not empty_data.meta.orders.create
        assert not empty_data.meta.orders.read
        assert not empty_data.meta.orders.update
        assert not empty_data.meta.orders.delete

    @staticmethod
    def test_wrong_init() -> None:
        ccd = ComponentConfigData
        with raises(ValueError, match="repeat"):
            ccd(ComponentMeta(members=[*([ComponentMember("repeat")] * 3)]))

        with raises(ValueError, match="alias"):
            ccd(ComponentMeta(members=[ComponentMember("same", alias="same")]))

        with raises(ValueError, match="members"):
            ccd(members={"not in meta": MappingConfigData()})

        with raises(ValueError, match="members"):
            ccd(meta=ComponentMeta(members=[ComponentMember("not in members")]))

    @staticmethod
    def test_readonly_attr(empty_data: CCD) -> None:
        for attr in ("meta", "members", "filename2meta", "alias2filename"):
            getattr(empty_data, attr)
            with raises(AttributeError):
                setattr(empty_data, attr, None)

    RetrieveTests: tuple[str, tuple[tuple[CCD, str, Any, EE, dict[str, Any]], ...]] = (
        "data, path, value, ignore_excs, kwargs",
        (
            (
                _ccd_from_meta(
                    {"members": ["a", "b", "c"]},
                    {"a": MappingConfigData(), "b": MappingConfigData(), "c": MappingConfigData({"key": "value"})},
                ),
                "key",
                "value",
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "b", "c"]},
                    {
                        "a": MappingConfigData({"foo": {"bar": "value"}}),
                        "b": MappingConfigData(),
                        "c": MappingConfigData(),
                    },
                ),
                "foo\\.bar",
                "value",
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "b", "c"]},
                    {
                        "a": MappingConfigData(),
                        "b": MappingConfigData({"foo": {"bar": "value"}}),
                        "c": MappingConfigData(),
                    },
                ),
                "foo\\.bar",
                "value",
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "b", "c"]},
                    {
                        "a": MappingConfigData(),
                        "b": MappingConfigData(),
                        "c": MappingConfigData({"foo": {"bar": "value"}}),
                    },
                ),
                "foo\\.bar",
                "value",
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", "a", "c"]},
                    {
                        "a": MappingConfigData(),
                        "b": MappingConfigData(),
                        "c": MappingConfigData({"foo": {"bar": "value"}}),
                    },
                ),
                "foo",
                {"bar": "value"},
                (),
                {"return_raw_value": True},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "c", "b"]},
                    {
                        "a": MappingConfigData(),
                        "b": MappingConfigData({"key": True}),
                        "c": MappingConfigData({"key": "value"}),
                    },
                ),
                "key",
                "value",
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "c", "b"]},
                    {
                        "a": MappingConfigData(pmap()),
                        "b": MappingConfigData(pmap({"key": True})),
                        "c": MappingConfigData(pmap({"key": "value"})),
                    },
                ),
                "key",
                "value",
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": [{"filename": "a", "alias": "c"}, "b"], "order": ["c"]},
                    {"a": MappingConfigData({"a": "value"}), "b": MappingConfigData({"b": True})},
                ),
                "a",
                "value",
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "b"]},
                    {"a": SequenceConfigData([{"key": False}]), "b": SequenceConfigData([{"key": True}])},
                ),
                "\\[0\\]\\.key",
                False,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "b"]},
                    {"a": SequenceConfigData([{"key": False}]), "b": SequenceConfigData([{"key": True}])},
                ),
                "\\{b\\}\\[0\\]\\.key",
                True,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "b", "c"]},
                    {
                        "a": MappingConfigData(),
                        "b": MappingConfigData({"key": False}),
                        "c": MappingConfigData({"key": None}),
                    },
                ),
                "\\{c\\}\\.key",
                None,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", {"filename": "a", "alias": "c"}]},
                    {"a": MappingConfigData({"key": False}), "b": MappingConfigData({"key": None})},
                ),
                "\\{c\\}\\.key",
                False,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", {"filename": "a", "alias": "c"}]},
                    {"a": MappingConfigData({"key": False}), "b": MappingConfigData({"key": None})},
                ),
                "\\{z\\}\\.key",
                None,
                (RequiredPathNotFoundError,),
                {},
            ),
            (
                _ccd_from_meta(
                    {"order": ["z"]},
                    {},
                ),
                "",
                None,
                (KeyError,),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "c", "b"]},
                    {
                        "a": MappingConfigData({"foo": "value"}),
                        "b": MappingConfigData({"foo": {"bar": "value"}}),
                        "c": MappingConfigData({"foo": {"bar": {"baz": "value"}}}),
                    },
                ),
                "foo\\.bar\\.baz\\.qux",
                None,
                (ConfigDataTypeError,),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "b"]},
                    {"a": MappingConfigData({"a": "value"}), "b": MappingConfigData({"b": True})},
                ),
                "key",
                None,
                (RequiredPathNotFoundError,),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a"], "order": []},
                    {"a": NoneConfigData()},  # type: ignore[dict-item]
                ),
                "",
                None,
                (RequiredPathNotFoundError,),
                {},
            ),
        ),
    )

    @staticmethod
    @mark.parametrize(*RetrieveTests)
    def test_retrieve(data: CCD, path: str, value: Any, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        with safe_raises(ignore_excs):
            assert data.retrieve(path, **kwargs) == value

    ModifyTests: tuple[str, tuple[tuple[CCD, str, Any, EE, dict[str, Any]], ...]] = (
        "data, path, value, ignore_excs, kwargs",
        (
            (
                _ccd_from_meta(
                    {"members": [{"filename": "a", "alias": "c"}, "b"], "order": ["c"]},
                    {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData()},
                ),
                "key",
                True,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "b"]},
                    {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData()},
                ),
                "key",
                True,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", "a"]},
                    {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData()},
                ),
                "key",
                True,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "b"], "orders": {"read": ["a", "b"], "update": ["b", "a"]}},
                    {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData()},
                ),
                "key",
                "value",
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", "a"]},
                    {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData({"key": None})},
                ),
                "key",
                True,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", "a"]},
                    {"a": MappingConfigData({"foo": {"bar": "value"}}), "b": MappingConfigData({"foo": {"bar": None}})},
                ),
                "foo\\.bar",
                True,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", "a"]},
                    {
                        "a": SequenceConfigData([{"foo": {"bar": "value"}}]),
                        "b": SequenceConfigData([{"foo": {"bar": None}}]),
                    },
                ),
                "\\[0\\]\\.foo\\.bar",
                True,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", "a"]},
                    {
                        "a": SequenceConfigData([{"foo": {"bar": "value"}}]),
                        "b": SequenceConfigData([{"foo": {"bar": None}}]),
                    },
                ),
                "\\{a\\}\\[0\\]\\.foo\\.bar",
                True,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", "a"]},
                    {"a": MappingConfigData({"foo": {"bar": "value"}}), "b": MappingConfigData({"foo": {"bar": None}})},
                ),
                "foo",
                {"bar": True},
                (),
                {"allow_create": False},
            ),
            (
                _ccd_from_meta(
                    {"members": ["c", "b", "a"]},
                    {
                        "a": MappingConfigData(),
                        "b": MappingConfigData({"key": False}),
                        "c": MappingConfigData({"key": None}),
                    },
                ),
                "\\{a\\}\\.key",
                True,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", {"filename": "a", "alias": "c"}]},
                    {"a": MappingConfigData({"key": False}), "b": MappingConfigData({"key": None})},
                ),
                "\\{c\\}\\.key",
                True,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", {"filename": "a", "alias": "c"}]},
                    {"a": MappingConfigData({"key": False}), "b": MappingConfigData({"key": None})},
                ),
                "\\{z\\}\\.key",
                None,
                (RequiredPathNotFoundError,),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", "a"]},
                    {"a": MappingConfigData({"foo": {"bar": "value"}}), "b": MappingConfigData({"foo": {"bar": None}})},
                ),
                "quz",
                {"value": True},
                (RequiredPathNotFoundError,),
                {"allow_create": False},
            ),
        ),
    )

    @staticmethod
    @mark.parametrize(*ModifyTests)
    def test_modify(data: CCD, path: str, value: Any, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        with safe_raises(ignore_excs) as info:
            data.modify(path, value, **kwargs)
        if info:
            return
        assert data.retrieve(path, return_raw_value=True) == value

    DeleteTests: tuple[str, tuple[tuple[CCD, str, Any, EE, dict[str, Any]], ...]] = (
        "data, path, value, ignore_excs, kwargs",
        (
            (
                _ccd_from_meta(
                    {"members": ["a", "b"]},
                    {
                        "a": MappingConfigData({"foo": {"bar": "value"}}),
                        "b": MappingConfigData({"foo": {"bar": False}}),
                    },
                ),
                "foo\\.bar",
                False,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": [{"filename": "a", "alias": "c"}, "b"], "order": ["c"]},
                    {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData({"key": "value"})},
                ),
                "key",
                Unset,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "b"], "orders": {"delete": ["b", "a"], "read": ["a", "b"]}},
                    {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData({"key": "value"})},
                ),
                "key",
                "value",
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "b", "c"]},
                    {
                        "a": MappingConfigData(),
                        "b": MappingConfigData({"key": False}),
                        "c": MappingConfigData({"key": None}),
                    },
                ),
                "\\{c\\}\\.key",
                False,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", {"filename": "a", "alias": "c"}]},
                    {"a": MappingConfigData({"key": False}), "b": MappingConfigData({"key": True})},
                ),
                "\\{c\\}\\.key",
                True,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", "a"]},
                    {"a": SequenceConfigData([{"key": False}]), "b": SequenceConfigData([{"key": True}])},
                ),
                "\\[0\\]\\.key",
                False,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", "a"]},
                    {"a": SequenceConfigData([{"key": False}]), "b": SequenceConfigData([{"key": True}])},
                ),
                "\\{a\\}\\[0\\]\\.key",
                Unset,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", {"filename": "a", "alias": "c"}]},
                    {"a": MappingConfigData({"key": False}), "b": MappingConfigData({"key": None})},
                ),
                "\\{z\\}\\.key",
                Unset,
                (RequiredPathNotFoundError,),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "b"], "order": []},
                    {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData({"key": "value"})},
                ),
                "key",
                Unset,
                (RequiredPathNotFoundError,),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "b"]},
                    {"a": MappingConfigData(), "b": MappingConfigData()},
                ),
                "key",
                Unset,
                (RequiredPathNotFoundError,),
                {},
            ),
        ),
    )

    @staticmethod
    @mark.parametrize(*DeleteTests)
    def test_delete(data: CCD, path: str, value: Any, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        with safe_raises(ignore_excs) as info:
            data.delete(path, **kwargs)
        if info:
            return
        assert data.get(path, value) == value

    UnsetTests: tuple[str, tuple[tuple[CCD, str, Any, EE, dict[str, Any]], ...]] = (
        "data, path, value, ignore_excs, kwargs",
        (
            (
                _ccd_from_meta(
                    {"members": ["a", "b"]},
                    {
                        "a": MappingConfigData({"foo": {"bar": "value"}}),
                        "b": MappingConfigData({"foo": {"bar": False}}),
                    },
                ),
                "foo\\.bar",
                False,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": [{"filename": "a", "alias": "c"}, "b"], "order": ["c"]},
                    {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData({"key": "value"})},
                ),
                "key",
                Unset,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "b"], "orders": {"delete": ["b", "a"], "read": ["a", "b"]}},
                    {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData({"key": "value"})},
                ),
                "key",
                "value",
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "b"], "order": []},
                    {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData({"key": "value"})},
                ),
                "key",
                "value",
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "b"]},
                    {"a": MappingConfigData(), "b": MappingConfigData()},
                ),
                "key",
                "value",
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "b", "c"]},
                    {
                        "a": MappingConfigData(),
                        "b": MappingConfigData({"key": False}),
                        "c": MappingConfigData({"key": None}),
                    },
                ),
                "\\{c\\}\\.key",
                False,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", {"filename": "a", "alias": "c"}]},
                    {"a": MappingConfigData({"key": False}), "b": MappingConfigData({"key": True})},
                ),
                "\\{c\\}\\.key",
                True,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", {"filename": "a", "alias": "c"}]},
                    {"a": MappingConfigData({"key": False}), "b": MappingConfigData({"key": None})},
                ),
                "\\{z\\}\\.key",
                Unset,
                (),
                {},
            ),
        ),
    )

    @staticmethod
    @mark.parametrize(*UnsetTests)
    def test_unset(data: CCD, path: str, value: Any, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        with safe_raises(ignore_excs) as info:
            data.unset(path, **kwargs)
        if info:
            return
        assert data.get(path, value) == value

    ExistsTests: tuple[str, tuple[tuple[CCD, str, bool, EE, dict[str, Any]], ...]] = (
        "data, path, is_exists, ignore_excs, kwargs",
        (
            (
                _ccd_from_meta(
                    {"members": ["a", "b"]},
                    {
                        "a": MappingConfigData({"foo": {"bar": None}}),
                        "b": MappingConfigData({"foo": {"bar": {"quz": None}}}),
                    },
                ),
                "foo\\.bar\\.quz",
                True,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", "a"]},
                    {
                        "a": MappingConfigData({"foo": {"bar": None}}),
                        "b": MappingConfigData({"foo": {"bar": {"quz": None}}}),
                    },
                ),
                "foo\\.bar\\.quz",
                True,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "b"]},
                    {"a": MappingConfigData(), "b": MappingConfigData()},
                ),
                "key",
                False,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "b"]},
                    {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData()},
                ),
                "key",
                True,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", "a"]},
                    {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData()},
                ),
                "key",
                False,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", "a"]},
                    {"a": SequenceConfigData([{"key": "value"}]), "b": SequenceConfigData([{}])},
                ),
                "\\[0\\]\\.key",
                False,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", "a"]},
                    {"a": SequenceConfigData([{"key": "value"}]), "b": SequenceConfigData([{}])},
                ),
                "\\{a\\}\\[0\\]\\.key",
                True,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {},
                    {},
                ),
                "key",
                False,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "b", "c"]},
                    {
                        "a": MappingConfigData(),
                        "b": MappingConfigData({"key": False}),
                        "c": MappingConfigData({"key": None}),
                    },
                ),
                "\\{c\\}\\.key",
                True,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "b", "c"]},
                    {
                        "a": MappingConfigData({"key": False}),
                        "b": MappingConfigData(),
                        "c": MappingConfigData({"key": None}),
                    },
                ),
                "\\{b\\}\\.key",
                False,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", {"filename": "a", "alias": "c"}]},
                    {"a": MappingConfigData({"key": False}), "b": MappingConfigData({"key": True})},
                ),
                "\\{c\\}\\.key",
                True,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", {"filename": "a", "alias": "c"}]},
                    {"a": MappingConfigData({"key": False}), "b": MappingConfigData({"key": True})},
                ),
                "\\{c\\}\\.any",
                False,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", {"filename": "a", "alias": "c"}]},
                    {"a": MappingConfigData({"key": False}), "b": MappingConfigData({"key": None})},
                ),
                "\\{z\\}\\.key",
                False,
                (),
                {},
            ),
        ),
    )

    @staticmethod
    @mark.parametrize(*ExistsTests)
    def test_exists(data: CCD, path: str, is_exists: bool, ignore_excs: EE, kwargs: dict[str, Any]) -> None:  # noqa: FBT001
        with safe_raises(ignore_excs):
            assert data.exists(path, **kwargs) is is_exists

    GetTests: tuple[str, tuple[tuple[CCD, str, Any, EE, dict[str, Any]], ...]] = (
        "data, path, value, ignore_excs, kwargs",
        (
            (
                _ccd_from_meta(
                    {},
                    {},
                ),
                "value",
                None,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "b"]},
                    {"a": MappingConfigData({"foo": {"bar": True}}), "b": MappingConfigData({"foo": {"bar": False}})},
                ),
                "foo\\.bar",
                True,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["b", "a"]},
                    {"a": MappingConfigData({"foo": {"bar": True}}), "b": MappingConfigData({"foo": {"bar": False}})},
                ),
                "foo\\.bar",
                False,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {},
                    {},
                ),
                "value",
                None,
                (),
                {},
            ),
        ),
    )

    @staticmethod
    @mark.parametrize(*GetTests)
    def test_get(data: CCD, path: str, value: Any, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        with safe_raises(ignore_excs):
            assert data.get(path, value, **kwargs) == value

    SetDefaultTests: tuple[str, tuple[tuple[CCD, str, Any, EE, dict[str, Any]], ...]] = (
        "data, path, value, ignore_excs, kwargs",
        (
            (
                _ccd_from_meta({"members": ["a", "b"]}, {"a": MappingConfigData(), "b": MappingConfigData()}),
                "test\\.path",
                None,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "b"], "orders": {"create": ["b", "a"], "read": ["a", "b"]}},
                    {"a": MappingConfigData(), "b": MappingConfigData()},
                ),
                "test\\.path",
                True,
                (),
                {},
            ),
            (
                _ccd_from_meta(
                    {"members": ["a", "b"], "orders": {"create": ["b", "a"], "read": ["a", "b"]}},
                    {"a": MappingConfigData(), "b": MappingConfigData({"test": {"path": None}})},
                ),
                "test\\.path",
                False,
                (AssertionError,),
                {},
            ),
            (_ccd_from_meta({}, {}), "test\\.path", None, (RequiredPathNotFoundError,), {}),
        ),
    )

    @staticmethod
    @mark.parametrize(*SetDefaultTests)
    def test_set_default(data: CCD, path: str, value: Any, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        with safe_raises(ignore_excs) as info:
            assert data.setdefault(path, value, **kwargs) == value
        if info:
            return
        assert data.retrieve(path, return_raw_value=True) == value

    @staticmethod
    @mark.parametrize(
        "a, b",
        (
            ({}, {}),
            (
                {},
                {"a": MappingConfigData()},
            ),
            (
                {"a": MappingConfigData()},
                {"a": MappingConfigData()},
            ),
            (
                {},
                {"a": MappingConfigData({"foo": "bar"}), "b": MappingConfigData({"foo": "quz"})},
            ),
            (
                {"a": MappingConfigData({"foo": "bar"}), "b": MappingConfigData({"foo": "quz"})},
                {"a": MappingConfigData({"foo": "bar"}), "b": MappingConfigData({"foo": "quz"})},
            ),
        ),
    )
    def test_eq(a: M, b: M) -> None:
        is_eq = a == b
        a, b = _ccd_from_members(a), _ccd_from_members(b)

        assert (a == b) is is_eq
        assert (not a != b) is is_eq  # noqa: SIM202
        assert not a == {}  # noqa: SIM201
        assert b != {}

    @staticmethod
    @mark.parametrize(
        "members",
        (
            {},
            {"a": MappingConfigData()},
            {"a": MappingConfigData({"foo": "bar"}), "b": MappingConfigData({"foo": "quz"})},
        ),
    )
    def test_str(members: M) -> None:
        assert str(members) in str(_ccd_from_members(members))

    @staticmethod
    @mark.parametrize(
        "members",
        (
            {},
            {"a": MappingConfigData()},
            {"a": MappingConfigData({"foo": "bar"}), "b": MappingConfigData({"foo": "quz"})},
        ),
    )
    def test_repr(members: M) -> None:
        ccd = _ccd_from_members(members)
        assert repr(members) in repr(ccd)

    @staticmethod
    @mark.parametrize(
        "members",
        (
            {},
            {"a": MappingConfigData()},
            {"a": MappingConfigData({"foo": "bar"}), "b": MappingConfigData({"foo": "quz"})},
        ),
    )
    def test_deepcopy(members: M) -> None:
        ccd = _ccd_from_members(members)
        copied = deepcopy(ccd)

        assert copied == ccd
        assert copied is not ccd

    @staticmethod
    @mark.parametrize(
        "members, key",
        (
            ({"a": MappingConfigData()}, "a"),
            ({"a": MappingConfigData()}, "b"),
            ({"a": MappingConfigData({"foo": "bar"}), "b": MappingConfigData({"foo": "quz"})}, "b"),
        ),
    )
    def test_contains(members: M, key: str) -> None:
        assert (key in _ccd_from_members(members)) is (key in members)

    @staticmethod
    @mark.parametrize(
        "members",
        (
            {"a": MappingConfigData(), "b": MappingConfigData()},
            {"a": MappingConfigData({"foo": "bar"}), "b": MappingConfigData({"foo": "quz"})},
            {"a": MappingConfigData({"foo": {"extra": "value"}}), "b": MappingConfigData({"foo": {"key": "value"}})},
        ),
    )
    def test_iter(members: M) -> None:
        assert list(_ccd_from_members(members)) == list(members.keys())

    @staticmethod
    @mark.parametrize(
        "members",
        (
            {},
            {"a": MappingConfigData()},
            {"a": MappingConfigData(), "b": MappingConfigData()},
            {"a": MappingConfigData(), "b": MappingConfigData(), "c": MappingConfigData()},
        ),
    )
    def test_len(members: M) -> None:
        assert len(_ccd_from_members(members)) == len(members)

    @staticmethod
    @mark.parametrize(
        "members, key",
        (
            ({}, "key"),
            ({"a": MappingConfigData({"key": "a"})}, "a"),
            ({"a": MappingConfigData({"key": "a"}), "b": MappingConfigData({"key": "b"})}, "b"),
        ),
    )
    def test_getitem(members: M, key: str) -> None:
        ignore_excs = []
        if key not in members:
            ignore_excs.append(KeyError)

        with safe_raises(tuple(ignore_excs)):
            assert _ccd_from_members(members)[key] == members[key]

    @staticmethod
    @mark.parametrize(
        "members, key, value",
        (
            ({}, "key", MappingConfigData()),
            ({"a": MappingConfigData()}, "a", MappingConfigData({"key": "value"})),
            ({"a": MappingConfigData()}, "b", MappingConfigData()),
        ),
    )
    def test_setitem(members: M, key: str, value: MappingConfigData[dict[Any, Any]]) -> None:
        ccd = _ccd_from_members(members)
        ccd[key] = value
        assert ccd[key] == value

    @staticmethod
    @mark.parametrize(
        "members, key",
        (
            ({}, "key"),
            ({"a": MappingConfigData()}, "a"),
            ({"a": MappingConfigData(), "b": MappingConfigData()}, "a"),
        ),
    )
    def test_delitem(members: M, key: str) -> None:
        ccd = _ccd_from_members(members)
        ignore_excs = []
        if key not in members:
            ignore_excs.append(KeyError)

        with safe_raises(tuple(ignore_excs)):
            del ccd[key]
        assert key not in ccd
