from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import closing
import subprocess
from tqdm import tqdm
import requests


def download_file(url, local_filename):
    # 创建一个Session对象
    s = requests.Session()
    # 设置User-Agent，模拟浏览器访问
    s.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:55.0) Gecko/20100101 Firefox/55.0'})
    # stream=True 参数会启用流式下载
    r = s.get(url, stream=True)
    # 把文件保存到本地
    with open(local_filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk: # 过滤掉保持连接的chunk
                f.write(chunk)
    return local_filename

def test_single_stream(name, url):
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
    except subprocess.CalledProcessError:
        return None
    except subprocess.TimeoutExpired:
        return None

    data = result.stdout
    # 解析 JSON 数据并处理
    import json
    data = json.loads(data)
    streams = data.get("streams", [])
    format_info = data.get("format", {})

    # 处理 streams 和 format 信息
    for stream in streams:
        if "codec_type" in stream and stream["codec_type"] == "video":
            resolution = str(stream.get("coded_width", "unknown")) + "x" + str(stream.get("coded_height", "unknown"))
            break
    else:
        resolution = "unknown"

    return {
        "Name": name,
        "URL": url,
        "Resolution": resolution
    }

def write_to_files(stream, output_base, resolution_files):
    resolution = stream['Resolution']
    if resolution != "unknown":
        try:
            width, height = resolution.split('x')
            filename = f"{output_base}_{height}p.txt"
        except ValueError:
            filename = f"{output_base}_unknown.txt"
    else:
        filename = f"{output_base}_unknown.txt"

    # 如果文件还未被创建，则创建一个新的文件
    if filename not in resolution_files:
        resolution_files[filename] = open(filename, 'a', encoding='utf-8') # 以附加模式打开
        print(f"Creating file for resolution {resolution}: {filename}")

    file = resolution_files[filename]
    file.write(f"{stream['Name']},{stream['URL']},{stream['Resolution']}\n")


import os
import re


def natural_sort_key(s):
    """Convert text to a list of strings and numbers that gives a natural sorting order."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

def is_valid_output_file(file_name):
    """Check if the file name matches the pattern 'output_<number>'."""
    match = re.match(r'output_([0-9]+)p\.txt$', file_name)
    return bool(match)

def merge_files(directory, output_file):
    # 获取指定目录下的所有文件名
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    # 过滤出符合特定模式的文件名
    output_files = [f for f in files if is_valid_output_file(f)]
    # 按照文件名中的数字进行自然排序
    sorted_files = sorted(output_files, key=natural_sort_key, reverse=True)
    # 合并文件
    with open(output_file, 'w') as outfile:
        for file_name in sorted_files:
            file_path = os.path.join(directory, file_name)
            with open(file_path, 'r') as infile:
                for line in infile:
                    outfile.write(line)

    # 删除原始的 output* 文件
    for file_name in sorted_files:
        file_path = os.path.join(directory, file_name)
        os.remove(file_path)

def read_file(file_name):
    with open(file_name, 'r', encoding='utf-8') as file:
        lines = file.read().splitlines()
    return lines

def write_file(file_name, lines):
    with open(file_name, 'w', encoding='utf-8') as file:
        file.writelines('\n'.join(lines))

def check_string_in_list(string, string_list):
    out = []
    for str in string:
        tmp = []
        if ',#genre#' in str:
            tmp.append(str)
        else:
            tmp = [item for item in string_list if str+',' in item]
            #tmp = [item for item in string_list if str+',' in item]
        out.extend(tmp)
    return out

def main(m3u_file, output_base, output_file):
#    resolution_files = {}
#    tasks = []
#
#    with open(m3u_file, 'r', encoding='utf-8') as file:
#        lines = file.readlines()
#
#    with ThreadPoolExecutor(max_workers=20) as executor:
#        for line in lines:
#            parts = line.strip().split(',')
#            if len(parts) >= 2:
#                name, url = parts[0], parts[1]
#                future = executor.submit(test_single_stream, name, url)
#                tasks.append(future)
#
#        for future in tqdm(as_completed(tasks), total=len(tasks)):
#            result = future.result()
#            if result:
#                write_to_files(result, output_base, resolution_files)
#
#    # 关闭所有文件
#    for file in resolution_files.values():
#        file.close()

    # 指定目录路径和输出文件名
    directory = "./"
    # 调用函数
    merge_files(directory, output_file)

    live_lines = read_file(output_file)
    template_lines = read_file("template.txt")
    
    result = check_string_in_list(template_lines, live_lines)
    write_file("result.txt", result)


if __name__ == "__main__":
    url = 'https://ghproxy.net/https://raw.githubusercontent.com/kimwang1978/collect-tv-txt/main/merged_output.txt'
    output_file = "live.txt"
    m3u_file = 'merged_output.txt'
    download_file(url, m3u_file)
    output_base = 'output'
    main(m3u_file, output_base, output_file)
    print("Streams have been sorted and written to separate files by resolution.")
    
