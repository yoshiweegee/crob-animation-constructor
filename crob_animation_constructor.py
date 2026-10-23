from argparse import ArgumentParser, BooleanOptionalAction
from collections.abc import Callable, Sequence, Iterable
from enum import StrEnum, auto as enum_auto
from fractions import Fraction
lazy from os import name as os_name
from pathlib import Path
from plistlib import InvalidFileException as PlistLibInvalidFileException, load as plistlib_load
from re import compile as re_compile
from reprlib import Repr
lazy from sys import version_info as sys_version_info
from subprocess import run, CalledProcessError, CompletedProcess
from typing import Any, Self, TypedDict, cast


class NeedModuleError(Exception):
    def __init__(self, module_name: str, package_name: str) -> None:
        super().__init__(
            "Module {} not found. It's likely that your Python doesn't have the {pn} package installed.\nTry running the following command in your command prompt/terminal to install the package: pip{} install --user {pn}".format(module_name, ".".join(str(version_component) for version_component in sys_version_info[:3]) if os_name == "posix" else "", pn=package_name))


def report_error(error: BaseException) -> None:
    if error.__cause__ is not None:
        report_error(error.__cause__)
    print(f"ERROR: {error}")


def exit_error(error: BaseException) -> None:
    report_error(error)
    exit(1)


try:
    from PIL import UnidentifiedImageError
    from PIL.Image import Image, Transpose, open as pil_image_open
except ModuleNotFoundError as module_error:
    if module_error.name is not None:
        try:
            raise NeedModuleError(module_error.name, "pillow") from module_error
        except NeedModuleError as e:
            exit_error(e)

Plist = list["Plist"] | str | dict[str, "Plist"] | float | int | str | bool
RE_INT2 = re_compile(r"^\{(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)}$")
RE_ARR_2 = re_compile(r"^\{(\{.+?}),(\{.+?})}$")


class AnimationFormat(StrEnum):
    WEBP = enum_auto()
    GIF = enum_auto()
    # AVIF = enum_auto()
    # JPEG_XL = enum_auto()


VERSION = [1, 0, 1]
VERSION_STRING = ".".join(str(component) for component in VERSION)

LIMITED_REPR_ITER_LIMIT = 16
LIMITED_REPR_OTHER_LIMIT = 64
limited_repr = Repr(
    maxtuple=LIMITED_REPR_ITER_LIMIT,
    maxlist=LIMITED_REPR_ITER_LIMIT,
    maxarray=LIMITED_REPR_ITER_LIMIT,
    maxdict=LIMITED_REPR_ITER_LIMIT,
    maxset=LIMITED_REPR_ITER_LIMIT,
    maxfrozenset=LIMITED_REPR_ITER_LIMIT,
    maxdeque=LIMITED_REPR_ITER_LIMIT,
    maxstring=LIMITED_REPR_OTHER_LIMIT,
    maxlong=LIMITED_REPR_OTHER_LIMIT,
    maxother=LIMITED_REPR_OTHER_LIMIT
)

FRAMES_DIR = "frames"
ANIM_DIR = "animations"


class FilePathInvalidError(Exception):
    def __init__(self, what_am_i: str, file_path: str) -> None:
        super().__init__(
            f"{what_am_i} not found at {file_path}. Make sure the path is correct and that a file exists there.")


class FileCannotBeOpenedError(Exception):
    def __init__(self, what_am_i: str, file_path: str) -> None:
        super().__init__(
            f"could not open {what_am_i} at {file_path}. Make sure the path is correct, that a file exists there, and that permissions are sufficient for accessing it, among other possible reasons.")


class InvalidPlistFileError(Exception):
    def __init__(self, what_am_i: str, file_path: str) -> None:
        super().__init__(
            f"{what_am_i} file at {file_path} is not a property list. Make sure the path leads to a property list.")


class PlistKeyError(Exception):
    def __init__(self, what_is_plist: str, what_is_value: str, key: str) -> None:
        super().__init__(f"{what_is_plist} does not have {what_is_value} at key \"{key}\".")


class TypeConversionError(Exception):
    def __init__(self, what_am_i: str, i_am_not_a: str) -> None:
        super().__init__(f"{what_am_i} is not {i_am_not_a}.")


class InvalidDirectoryPathError(Exception):
    def __init__(self, what_am_i: str, dir_path: str) -> None:
        super().__init__(
            f"{what_am_i} path at {dir_path} is invalid. Make sure the path is correct and that no step of the path is a file.")


class OutputInterruptedError(Exception):
    def __init__(self, what_am_i: str, file_path: str) -> None:
        super().__init__(
            f"output of {what_am_i} to {file_path} could not be completed. Make sure no other programs could be blocking access to the path, and that permissions are sufficient for accessing it.")


class SpriteSheetFormatUnrecognized(Exception):
    def __init__(self, file_path: str) -> None:
        super().__init__(
            f"sprite sheet file at {file_path} isn't recognized as an image. Make sure the path leads to an image.\nIf you're certain it's an image, it might not be supported. Try a different format.")


class CannotRunOutputProcessError(Exception):
    def __init__(self, program_name: str, readable_name: str) -> None:
        super().__init__(
            f"Could not run program to output an animation image. This likely because your PATH environment variable is missing the path to a program named \"{program_name}\". This might be caused by not having {readable_name} installed.")


class UnsuccessfulOutputError(Exception):
    def __init__(self, anim_name: str, completion_data: CompletedProcess) -> None:
        super().__init__(
            f"Something went wrong while outputting the animation {anim_name}. This might or might not be your fault. Check the following error log from the program. If garbled, report to developer.\n\n{completion_data.stderr}")


class Point2:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def __repr__(self) -> str:
        return f"Point2(x={repr(self.x)}, y={repr(self.y)})"


class Size2:
    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height

    def __repr__(self) -> str:
        return f"Size2(width={repr(self.width)}, height={repr(self.height)})"


class Rectangle:
    def __init__(self, left: int, top: int, width: int, height: int) -> None:
        self.left = left
        self.top = top
        self.width = width
        self.height = height

    def __repr__(self) -> str:
        return f"Rectangle(left={repr(self.left)}, top={repr(self.top)}, width={repr(self.width)}, height={repr(self.height)})"


class FrameInfoRaw(TypedDict):
    aliases: list[str]
    # offsets represent center of sprite from center of source
    # y-offsets are inverted
    spriteOffset: str
    spriteSize: str
    spriteSourceSize: str
    textureRect: str
    textureRotated: bool


class FrameData:
    def __init__(self, name: str, aliases: Iterable[str], sprite_offset: Point2, sprite_size: Size2,
                 sprite_source_size: Size2, texture_rect: Rectangle, texture_rotated: bool) -> None:
        self.name = name
        self.aliases = list(aliases)
        # y-offsets are flipped but still represent the top edge
        self.sprite_offset = sprite_offset
        self.sprite_size = sprite_size
        self.sprite_source_size = sprite_source_size
        self.texture_rect = texture_rect
        self.texture_rotated = texture_rotated

    # might raise PlistKeyError, TypeConversionError
    @classmethod
    def try_from_raw(cls, name: str, raw: dict[str, Plist]) -> Self:
        aliases = try_plist_dict_get(raw, "aliases", f"frame {name}", "aliases")
        aliases = try_reinterpret_plist_array(aliases, f"aliases of frame {name}")
        for index, alias in enumerate(aliases):
            try_reinterpret_str(alias, f"alias at index {index} of frame {name}")

        sprite_offset = try_plist_dict_get(raw, "spriteOffset", f"frame {name}", "sprite offset")
        sprite_offset = try_reinterpret_str(sprite_offset, f"sprite offset of frame {name}")
        sprite_offset = try_str_to_point2(sprite_offset, f"sprite offset of frame {name}")

        sprite_size = try_plist_dict_get(raw, "spriteSize", f"frame {name}", "sprite size")
        sprite_size = try_reinterpret_str(sprite_size, f"sprite size of frame {name}")
        sprite_size = try_str_to_size2(sprite_size, f"sprite size of frame {name}")

        sprite_source_size = try_plist_dict_get(raw, "spriteSourceSize", f"frame {name}", "sprite source size")
        sprite_source_size = try_reinterpret_str(sprite_source_size, f"sprite source size of frame {name}")
        sprite_source_size = try_str_to_size2(sprite_source_size, f"sprite source size of frame {name}")

        texture_rect = try_plist_dict_get(raw, "textureRect", f"frame {name}", "texture rectangle")
        texture_rect = try_reinterpret_str(texture_rect, f"texture rectangle of frame {name}")
        texture_rect = try_str_to_rect(texture_rect, f"texture rectangle of frame {name}")

        texture_rotated = try_plist_dict_get(raw, "textureRotated", f"frame {name}", "rotated texture flag")
        texture_rotated = try_reinterpret_bool(texture_rotated, f"rotated texture flag of frame {name}")

        return cls(name, cast(list[str], aliases), sprite_offset, sprite_size, sprite_source_size, texture_rect,
                   texture_rotated)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={repr(self.name)}, aliases={limited_repr.repr(self.aliases)}, spriteOffset={repr(self.sprite_offset)}, spriteSize={repr(self.sprite_size)}, spriteSourceSize={repr(self.sprite_source_size)}, textureRect={repr(self.texture_rect)}, textureRotated={repr(self.texture_rotated)})"


class AnimationInfo:
    def __init__(self, animations: dict[str, AnimationData], frame_list: Iterable[str]) -> None:
        self.animations = animations
        self.frame_list = list(frame_list)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(animations={limited_repr.repr(self.animations)}, frame_list={limited_repr.repr(self.frame_list)})"


class AnimationData:
    def __init__(self, name: str, seconds_per_frame: float, frame_list: Iterable[int]) -> None:
        self.name = name
        self.seconds_per_frame = seconds_per_frame
        self.frame_list = list(frame_list)

    # might raise PlistKeyError, TypeConversionError
    @classmethod
    def try_from_raw(cls, name: str, raw: dict[str, Plist]) -> Self:
        seconds_per_frame = try_plist_dict_get(raw, "FPS", f"animation {name}", "seconds per frame")
        seconds_per_frame = try_reinterpret_float(seconds_per_frame, f"seconds per frame of animation {name}")

        frame_list = try_plist_dict_get(raw, "FrameList", f"animation {name}", "frame list")
        frame_list = try_reinterpret_plist_array(frame_list, f"frame list of animation {name}")
        for index, frame_index in enumerate(frame_list):
            try_reinterpret_int(frame_index, f"frame index at index {index} of animation {name}")

        return cls(name, seconds_per_frame, cast(list[int], frame_list))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, seconds_per_frame={repr(self.seconds_per_frame)}, frame_list={limited_repr.repr(self.frame_list)})"


class FrameArgs:
    def __init__(self, delay: Fraction, image_input: str, offset: Point2) -> None:
        self.delay = delay
        self.image_input = image_input
        self.offset = offset

    def to_tuple(self) -> tuple[str, str, str, str, str, str, str]:
        return "(", "-delay", f"{self.delay.numerator}x{self.delay.denominator}", self.image_input, "-repage", f"{int_to_magick_offset(int(self.offset.x))}{int_to_magick_offset(int(self.offset.y))}", ")"


# handles strings in the format "{x,y}"
# might raise ValueError
def str_to_two_float(str_source: str) -> tuple[float, float]:
    two_int_match = RE_INT2.fullmatch(str_source)
    if two_int_match is None:
        raise ValueError("string is not correctly formatted as a list of two integers")
    return float(two_int_match[1]), float(two_int_match[2])


# might raise TypeConversionError
def try_str_to_point2(str_source: str, what_am_i: str = "unspecified") -> Point2:
    try:
        return Point2(*str_to_two_float(str_source))
    except ValueError as e:
        raise TypeConversionError(what_am_i, "a stringified 2D point") from e


# might raise TypeConversionError
def try_str_to_size2(str_source: str, what_am_i: str = "unspecified") -> Size2:
    try:
        return Size2(*str_to_two_float(str_source))
    except ValueError as e:
        raise TypeConversionError(what_am_i, "a stringified 2D size") from e


# handles strings in the format "{{l,t},{w,h}}"
# might raise TypeConversionError
def try_str_to_rect(str_source: str, what_am_i: str = "unspecified") -> Rectangle:
    possible_error = TypeConversionError(what_am_i, "a stringified rectangle")

    two_arr_match = RE_ARR_2.fullmatch(str_source)
    if two_arr_match is None:
        raise possible_error

    try:
        return Rectangle(*str_to_two_float(two_arr_match[1]), *str_to_two_float(two_arr_match[2]))
    except ValueError as e:
        raise possible_error from e


# might raise OSError, PlistLibInvalidFileException
def load_plist(file_path: str) -> Plist:
    with open(file_path, "rb") as plist_file:
        return plistlib_load(plist_file)


# might raise FileCannotBeOpened, InvalidPlistFile
def try_load_plist(file_path: str, what_am_i: str = "unspecified") -> Plist:
    try:
        return load_plist(file_path)
    except OSError as e:
        raise FileCannotBeOpenedError(what_am_i, file_path) from e
    except PlistLibInvalidFileException as e:
        raise InvalidPlistFileError(what_am_i, file_path) from e


# might raise PlistKeyError
def try_plist_dict_get(plist: dict[str, Plist], key: str, what_is_plist: str = "unspecified",
                       what_is_value: str = "anything") -> Plist:
    try:
        return plist[key]
    except KeyError as e:
        raise PlistKeyError(what_is_plist, what_is_value, key) from e


# might TypeConversionError
def assert_type(val: Any, expected_type: type, what_am_i: str = "unspecified",
                readable_type: str | None = None) -> None:
    if type(val) != expected_type:
        if readable_type is None:
            readable_type = expected_type.__name__
        raise TypeConversionError(what_am_i, readable_type)


# might raise TypeConversionError
def try_reinterpret_plist_dict(val: Any, what_am_i: str = "unspecified") -> dict[str, Plist]:
    assert_type(val, dict, f"{what_am_i}", "a dictionary")
    return val


# might raise TypeConversionError
def try_reinterpret_plist_array(val: Any, what_am_i: str = "unspecified") -> list[Plist]:
    assert_type(val, list, f"{what_am_i}", "an array")
    return val


# might raise TypeConversionError
def try_reinterpret_str(val: Any, what_am_i: str = "unspecified") -> str:
    assert_type(val, str, f"{what_am_i}", "a string")
    return val


# might raise TypeConversionError
def try_reinterpret_bool(val: Any, what_am_i: str = "unspecified") -> bool:
    assert_type(val, bool, f"{what_am_i}", "a boolean")
    return val


# might raise TypeConversionError
def try_reinterpret_float(val: Any, what_am_i: str = "unspecified") -> float:
    assert_type(val, float, f"{what_am_i}", "a float")
    return val


# might raise TypeConversionError
def try_reinterpret_int(val: Any, what_am_i: str = "unspecified") -> int:
    assert_type(val, int, f"{what_am_i}", "an integer")
    return val


def get_frame_top_left(frame: FrameData) -> Point2:
    return Point2(
        (frame.sprite_source_size.width - frame.sprite_size.width) / 2 + frame.sprite_offset.x,
        (frame.sprite_source_size.height - frame.sprite_size.height) / 2 - frame.sprite_offset.y
    )


def int_to_magick_offset(val: int) -> str:
    return str(val) if val < 0 else f"+{val}"


# might raise FileCannotBeOpened, InvalidPlistFile, TypeConversionError, PlistKeyError
def try_load_frames_table(file_path: str) -> dict[str, FrameData]:
    print("Loading frames info...")
    frames_plist = try_load_plist(file_path, "frames info")
    frames_plist = try_reinterpret_plist_dict(frames_plist, "frames info")

    raw_frames_table = try_plist_dict_get(frames_plist, "frames", "frames info", "frames table")
    raw_frames_table = try_reinterpret_plist_dict(raw_frames_table, "frames table")

    print("Parsing frames...")
    frames_table: dict[str, FrameData] = {}
    for frame_name, raw_frame_info in raw_frames_table.items():
        raw_frame_info = try_reinterpret_plist_dict(raw_frame_info, f"frame {frame_name}")

        try:
            frames_table[frame_name] = FrameData.try_from_raw(frame_name, raw_frame_info)
        except (TypeConversionError, PlistKeyError) as e:
            raise TypeConversionError(f"frame {frame_name}", "a frame") from e

    return frames_table


def try_load_anim_info(file_path: str) -> AnimationInfo:
    print("Loading animation info...")
    anim_info_plist = try_load_plist(file_path, "anim info")
    anim_info_plist = try_reinterpret_plist_dict(anim_info_plist, "anim info")

    frames_list = try_plist_dict_get(anim_info_plist, "framelist", "anim info", "frame list")
    frames_list = try_reinterpret_plist_array(frames_list, "frame list")
    for index, frame_name in enumerate(frames_list):
        try_reinterpret_str(frame_name, f"frame name at index {index} of frame list")

    raw_anim_table = try_plist_dict_get(anim_info_plist, "animationlist", "anim info", "animation table")
    raw_anim_table = try_reinterpret_plist_dict(raw_anim_table, "animation table")

    print("Parsing animations...")
    anim_table: dict[str, AnimationData] = {}
    for anim_name, raw_anim_info in raw_anim_table.items():
        raw_anim_info = try_reinterpret_plist_dict(raw_anim_info, f"animation {anim_name}")

        try:
            anim_table[anim_name] = AnimationData.try_from_raw(anim_name, raw_anim_info)
        except (TypeConversionError, PlistKeyError) as e:
            raise TypeConversionError(f"animation {anim_name}", "an animation") from e

    return AnimationInfo(anim_table, cast(list[str], frames_list))


def get_frame_args(frame: FrameData | None, delay: Fraction, canvas: Rectangle, output_dir: str) -> FrameArgs:
    if frame is None:
        return FrameArgs(delay, "xc:transparent[1x1!]", Point2(0, 0))
    else:
        frame_top_left = get_frame_top_left(frame)
        return FrameArgs(delay, str(Path(output_dir) / FRAMES_DIR / frame.name),
                         Point2(frame_top_left.x - canvas.left, frame_top_left.y - canvas.top))


# might raise CannotRunOutputProcessError, UnsuccessfulOutputError
def output_with_magick(output_dir: str, anim_name: str, frames: Sequence[FrameData | None],
                       seconds_per_frame: float, extension: str, format_specific_args: Iterable[str]) -> None:
    if len(frames) == 0:
        # WHAT ARE YOU DOING??
        return

    # determine the canvas size based on position and size of all frames
    first_real_frame_index: int | None
    first_real_frame: FrameData | None
    first_real_frame_index, first_real_frame = next(
        ((index, frame) for index, frame in enumerate(frames) if frame is not None), (None, None))
    if first_real_frame is None:
        canvas = Rectangle(0, 0, 1, 1)
    else:
        first_frame_top_left = get_frame_top_left(first_real_frame)
        canvas = Rectangle(int(first_frame_top_left.x), int(first_frame_top_left.y),
                           int(first_real_frame.sprite_size.width),
                           int(first_real_frame.sprite_size.height))

        for frame in frames[first_real_frame_index + 1:]:
            if frame is not None:
                frame_top_left = get_frame_top_left(frame)
                if frame_top_left.x < canvas.left:
                    canvas.width += int(canvas.left - frame_top_left.x)
                    canvas.left = int(frame_top_left.x)
                if frame_top_left.y < canvas.top:
                    canvas.height += int(canvas.top - frame_top_left.y)
                    canvas.top = int(frame_top_left.y)
                if frame_top_left.x + frame.sprite_size.width > canvas.left + canvas.width:
                    canvas.width = int(frame_top_left.x + frame.sprite_size.width) - canvas.left
                if frame_top_left.y + frame.sprite_size.height > canvas.top + canvas.height:
                    canvas.height = int(frame_top_left.y + frame.sprite_size.height) - canvas.top

    rational_framerate = Fraction(seconds_per_frame).limit_denominator(1000)
    frame_args = [get_frame_args(frames[0], rational_framerate, canvas, output_dir)]
    last_display_frame = frames[0]
    for frame in frames[1:]:
        if frame == last_display_frame:
            frame_args[-1].delay += rational_framerate
            continue

        frame_args.append(get_frame_args(frame, rational_framerate, canvas, output_dir))
        last_display_frame = frame

    frame_args: Iterable[str] = (arg for frame_args_data in frame_args for arg in frame_args_data.to_tuple())

    print(f"Writing animation {anim_name}...")
    try:
        completion_data = run(
            (
                "magick",
                "-dispose", "previous",  # necessary to avoid frame stacking
                *frame_args,
                "-repage", f"{canvas.width}x{canvas.height}",
                *format_specific_args,
                str(Path(output_dir) / ANIM_DIR / f"{anim_name}.{extension}")
            ),
            capture_output=True,
            text=True
        )
    except OSError as e:
        raise CannotRunOutputProcessError("magick", "ImageMagick") from e

    try:
        completion_data.check_returncode()
    except CalledProcessError as e:
        raise UnsuccessfulOutputError(anim_name, completion_data) from e


# might raise CannotRunOutputProcessError, UnsuccessfulOutputError
def output_anim_webp(output_dir: str, anim_name: str, frames: Sequence[FrameData | None],
                     seconds_per_frame: float) -> None:
    output_with_magick(output_dir, anim_name, frames, seconds_per_frame, "webp", (
        # IM's frame optimization is buggy with WebP
        # WebP doesn't usually benefit from transparency optimization
        "-quality", "100"  # lossless
    ))


def output_anim_gif(output_dir: str, anim_name: str, frames: Sequence[FrameData | None],
                    seconds_per_frame: float) -> None:
    output_with_magick(output_dir, anim_name, frames, seconds_per_frame, "gif", (
        "-coalesce",  # realize how the frame actually displays
        "-channel", "A",  # prepare to modify alpha
        "-ordered-dither", "o8x8",  # apply dither to transparency, as GIF has only binary transparency (on or off)
        # normally this would be just optimize, but weird artifacts appear after using ordered dither for some reason
        "-layers", "optimize-transparency",  # make parts that don't change between frames transparent (if possible)
        "-layers", "optimize-frame"  # crop frames
    ))


# might raise FileCannotBeOpenedError, InvalidPlistFileError, TypeConversionErrorError, PlistKeyError,
# InvalidDirectoryPathError, FilePathInvalidError, SpriteSheetFormatUnrecognizedError
def main() -> None:
    arg_parser = ArgumentParser(
        f"CookieRun: OvenBreak Animation Constructor {VERSION_STRING}",
        description="Constructs animations for CookieRun: OverBreak from relevant files",
    )
    arg_parser.add_argument(
        "sprite_sheet_file_name",
        help="Sprite sheet file path",
        metavar="sprite-sheet"
    )
    arg_parser.add_argument(
        "frames_plist_file_name",
        nargs="?",
        help="Frames property list file path. Defaults to a file named the same as the sprite sheet file but with extension \".plist\", in the same location as the sprite sheet",
        metavar="frames-plist"
    )
    arg_parser.add_argument(
        "anim_info_plist_file_name",
        nargs="?",
        help="Animation information property list file path. Defaults to a file in named the same as the sprite sheet file but followed by \"_aniinfo.plist\", in the same location as the sprite sheet",
        metavar="aniinfo-plist"
    )
    arg_parser.add_argument(
        "-o", "--output-directory",
        type=Path,
        help="Output directory path. Defaults to a directory named the stem of the sprite sheet file but followed by \"_data\", in the same place as the sprite sheet",
        dest="output_dir"
    )
    arg_parser.add_argument(
        "-af", "--animation-format",
        default=AnimationFormat.WEBP,
        choices=AnimationFormat,
        help="Output animation format. Defaults to WebP",
        dest="anim_fmt"
    )
    arg_parser.add_argument(
        "-v", "--version",
        action=BooleanOptionalAction,
        help="Display version and exit. Other arguments will be ignored",
    )
    args = arg_parser.parse_args()

    if args.version:
        print(VERSION_STRING)
        return

    # weird casts needed for pycharm 2026.2.3
    if cast(str | None, cast(object, args.frames_plist_file_name)) is None:
        args.frames_plist_file_name = Path(
            args.sprite_sheet_file_name).resolve().parent / f"{Path(args.sprite_sheet_file_name).stem}.plist"
    if cast(str | None, cast(object, args.anim_info_plist_file_name)) is None:
        args.anim_info_plist_file_name = Path(
            args.sprite_sheet_file_name).resolve().parent / f"{Path(args.sprite_sheet_file_name).stem}_aniinfo.plist"
    if cast(str | None, cast(object, args.output_dir)) is None:
        args.output_dir = Path(
            args.sprite_sheet_file_name).resolve().parent / f"{Path(args.sprite_sheet_file_name).stem}_data"

    frames_table = try_load_frames_table(str(args.frames_plist_file_name))

    frames_dir = args.output_dir / FRAMES_DIR
    try:
        frames_dir.mkdir(parents=True, exist_ok=True)
    except FileExistsError as e:
        raise InvalidDirectoryPathError("frames", str(frames_dir)) from e

    print("Loading sprite sheet...")
    try:
        sprite_sheet = pil_image_open(args.sprite_sheet_file_name)
    except FileNotFoundError as e:
        raise FilePathInvalidError("sprite sheet", args.sprite_sheet_file_name) from e
    except UnidentifiedImageError as e:
        raise SpriteSheetFormatUnrecognized(args.sprite_sheet_file_name) from e
    # ValueError, TypeError shouldn't happen

    print("Writing frames...")
    frame_images: dict[str, Image] = {}
    with sprite_sheet:
        for frame_name, frame_data in frames_table.items():
            sprite = sprite_sheet.crop((
                frame_data.texture_rect.left,
                frame_data.texture_rect.top,
                frame_data.texture_rect.left + (
                    frame_data.texture_rect.height if frame_data.texture_rotated else frame_data.texture_rect.width),
                frame_data.texture_rect.top + (
                    frame_data.texture_rect.width if frame_data.texture_rotated else frame_data.texture_rect.height)
            ))
            if frame_data.texture_rotated:
                sprite = sprite.transpose(Transpose.ROTATE_90)

            output_path = frames_dir / frame_name
            try:
                sprite.save(output_path)
            except OSError as e:
                raise OutputInterruptedError(f"frame {frame_name}", str(output_path)) from e
            # remember for making animations
            frame_images[frame_name] = sprite

    anim_info = try_load_anim_info(str(args.anim_info_plist_file_name))

    anim_dir = args.output_dir / ANIM_DIR
    try:
        anim_dir.mkdir(parents=True, exist_ok=True)
    except FileExistsError as e:
        raise InvalidDirectoryPathError("animations", str(anim_dir)) from e

    output_func: Callable[[str, str, Sequence[FrameData | None], float], None] = {
        AnimationFormat.WEBP: output_anim_webp,
        AnimationFormat.GIF: output_anim_gif
    }[args.anim_fmt]

    print("Writing animations...")
    for anim_name, anim_data in anim_info.animations.items():
        frames = tuple(
            frames_table[frame_name] if frame_name is not None and frame_name in frames_table else None
            for frame_name in (
                anim_info.frame_list[frame_index] if frame_index < len(anim_info.frame_list) else None
                for frame_index in anim_data.frame_list
            )
        )
        output_func(str(args.output_dir), anim_name, frames, anim_data.seconds_per_frame)

    print("Done!")


if __name__ == '__main__':
    try:
        main()
    except (FilePathInvalidError, FileCannotBeOpenedError, InvalidPlistFileError, PlistKeyError, TypeConversionError,
            InvalidDirectoryPathError, SpriteSheetFormatUnrecognized) as main_error:
        exit_error(main_error)
    except Exception:
        STANDARD_TERMINAL_WIDTH = 80
        DIVIDER = "=" * STANDARD_TERMINAL_WIDTH
        print("\n" + DIVIDER + "\nAn unexpected error occurred. Exception report below.\n" + DIVIDER, flush=True)
        raise
