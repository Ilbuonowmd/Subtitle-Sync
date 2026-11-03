
# -*- coding: utf-8 -*-
import os
import re
import sys
import shutil
import subprocess
from pathlib import Path
from fractions import Fraction

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"

FPS_MODES = [
    ("Không đổi FPS", None),
    ("23.976 -> 24", Fraction(1000, 1001)),
    ("23.976 -> 25", Fraction(960, 1001)),
    ("24 -> 23.976", Fraction(1001, 1000)),
    ("24 -> 25", Fraction(24, 25)),
    ("25 -> 23.976", Fraction(25025, 24000)),
    ("25 -> 24", Fraction(25, 24)),
]

TIMING_RE = re.compile(
    r"(?P<start>\d{2,}:\d{2}:\d{2}[,.]\d{3})"
    r"(?P<sep>\s+-->\s+)"
    r"(?P<end>\d{2,}:\d{2}:\d{2}[,.]\d{3})"
)


def find_supmover():
    for name in ("SupMover.exe", "supmover.exe"):
        path = SCRIPT_DIR / name
        if path.is_file():
            return str(path)
    return shutil.which("SupMover.exe") or shutil.which("supmover.exe")


def choose_fps():
    print("\nChọn chế độ FPS:")
    for i, (name, _) in enumerate(FPS_MODES, 1):
        print(f"  {i}. {name}")

    while True:
        choice = input("Nhập số 1-7: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= 7:
            return FPS_MODES[int(choice) - 1]
        print("Vui lòng nhập số từ 1 đến 7.")


def choose_delay():
    while True:
        try:
            return int(input(
                "Delay (ms; âm = sớm hơn, dương = trễ hơn): "
            ).strip())
        except ValueError:
            print("Nhập số nguyên, ví dụ -3000, 2500 hoặc 0.")


def get_inputs(args):
    result = []
    seen = set()

    for arg in args:
        path = Path(arg.strip('"')).resolve()

        if not path.exists():
            print(f"Bỏ qua đường dẫn không tồn tại: {path}")
            continue

        key = os.path.normcase(str(path))
        if key not in seen:
            seen.add(key)
            result.append(path)

    return result


def collect_files(inputs):
    jobs = []
    seen = set()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for item in inputs:
        if item.is_file():
            if item.suffix.lower() not in (".sup", ".srt"):
                print(f"Bỏ qua file không hỗ trợ: {item}")
                continue

            key = os.path.normcase(str(item.resolve()))
            if key in seen:
                continue

            # File lẻ: output/<tên file không có phần mở rộng>/<tên file>
            destination = OUTPUT_DIR / item.stem / item.name
            jobs.append((item, destination))
            seen.add(key)

        elif item.is_dir():
            # Thư mục nguồn: output/<tên thư mục>/<cấu trúc con>
            output_root = OUTPUT_DIR / item.name

            for current, dirs, filenames in os.walk(item):
                current_path = Path(current)

                # Tránh quét thư mục output và thư mục kết quả.
                dirs[:] = [
                    d for d in dirs
                    if d.lower() != "output"
                    and not d.lower().endswith("_synced")
                ]

                for filename in filenames:
                    source = current_path / filename

                    if source.suffix.lower() not in (".sup", ".srt"):
                        continue

                    key = os.path.normcase(str(source.resolve()))
                    if key in seen:
                        continue

                    relative = source.relative_to(item)
                    destination = output_root / relative
                    jobs.append((source, destination))
                    seen.add(key)

    return jobs


def timestamp_to_ms(value):
    value = value.replace(",", ".")
    hours, minutes, rest = value.split(":")
    seconds, millis = rest.split(".")
    return (
        (int(hours) * 3600 + int(minutes) * 60 + int(seconds)) * 1000
        + int(millis)
    )


def ms_to_timestamp(value):
    value = max(0, value)
    hours, value = divmod(value, 3600000)
    minutes, value = divmod(value, 60000)
    seconds, millis = divmod(value, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


def scale_time(value, factor):
    numerator = value * factor.numerator
    denominator = factor.denominator
    # Làm tròn đến mili giây gần nhất.
    return (2 * numerator + denominator) // (2 * denominator)


def read_srt(path):
    data = path.read_bytes()

    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig"), "utf-8-sig"

    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        # Fallback cho SRT ANSI trên Windows.
        return data.decode("cp1252"), "cp1252"


def process_srt(source, destination, factor, delay_ms):
    text, encoding = read_srt(source)
    count = 0

    def replace_timing(match):
        nonlocal count

        start = timestamp_to_ms(match.group("start"))
        end = timestamp_to_ms(match.group("end"))

        # Bước 1: đổi FPS.
        if factor is not None:
            start = scale_time(start, factor)
            end = scale_time(end, factor)

        # Bước 2: đặt delay.
        start += delay_ms
        end += delay_ms

        # SRT không hỗ trợ timestamp âm.
        start = max(0, start)
        end = max(0, end)

        if end <= start:
            end = start + 1

        count += 1
        return (
            ms_to_timestamp(start)
            + match.group("sep")
            + ms_to_timestamp(end)
        )

    result = TIMING_RE.sub(replace_timing, text)

    if count == 0:
        raise RuntimeError("Không tìm thấy dòng timestamp SRT hợp lệ.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with open(destination, "w", encoding=encoding, newline="") as f:
        f.write(result)

    return count


def process_sup(executable, source, destination, factor, delay_ms):
    if not executable:
        raise RuntimeError(
            "Không tìm thấy SupMover.exe. Hãy đặt nó cùng thư mục script."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)

    command = [executable, str(source), str(destination)]

    if factor is not None:
        command.extend([
            "--resync",
            f"{factor.numerator}/{factor.denominator}"
        ])

    if delay_ms != 0:
        command.extend(["--delay", str(delay_ms)])

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        errors="replace",
        shell=False
    )

    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())

    if result.returncode != 0 or not destination.is_file():
        raise RuntimeError(
            f"SupMover thất bại, mã lỗi: {result.returncode}"
        )


def main():
    if len(sys.argv) < 2:
        print("Kéo thả file .sup/.srt hoặc thư mục vào Subtitle_sync.bat.")
        input("Nhấn Enter để thoát...")
        return

    fps_name, factor = choose_fps()
    delay_ms = choose_delay()

    inputs = get_inputs(sys.argv[1:])
    jobs = collect_files(inputs)

    if not jobs:
        print("Không tìm thấy file .sup hoặc .srt.")
        input("Nhấn Enter để thoát...")
        return

    supmover = find_supmover()
    succeeded = 0
    failed = 0

    print(f"\nFPS: {fps_name}")
    print(f"Delay: {delay_ms} ms")
    print(f"Tổng file: {len(jobs)}")
    print(f"Output: {OUTPUT_DIR}\n")

    for index, (source, destination) in enumerate(jobs, 1):
        print(f"[{index}/{len(jobs)}] {source}")
        print(f" -> {destination}")

        try:
            if source.suffix.lower() == ".srt":
                count = process_srt(
                    source, destination, factor, delay_ms
                )
                print(f" OK - đã chỉnh {count} dòng thời gian\n")
            else:
                process_sup(
                    supmover, source, destination, factor, delay_ms
                )
                print(" OK\n")

            succeeded += 1

        except Exception as exc:
            failed += 1
            print(f" LỖI: {exc}\n")

    print("=== HOÀN TẤT ===")
    print(f"Thành công: {succeeded}")
    print(f"Thất bại: {failed}")
    input("Nhấn Enter để đóng...")


if __name__ == "__main__":
    main()
