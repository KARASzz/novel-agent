#!/usr/bin/env python3
"""
验证小说立项中台主链路中没有假成功路径。
"""
import re
import sys
from pathlib import Path


FORBIDDEN_PATTERNS = [
    r"\bmock\b", r"\bfake\b", r"\bdummy\b",
    r"default_success", r"fallback_success", r"default_pass",
]


def is_comment_or_string(line: str) -> bool:
    """检查是否为注释或字符串字面量"""
    stripped = line.strip()
    if stripped.startswith("#"):
        return True
    if '"""' in line or "'''" in line:
        return True
    return False


def check_file(path: Path, skip_own: bool = False) -> list[str]:
    """检查单个文件，返回违规行列表"""
    issues = []
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return [f"无法读取: {path}"]
    
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        if is_comment_or_string(line):
            continue
        
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                issues.append(f"  行 {i}: {line.strip()}")
    
    return issues


def main():
    dirs = ["pre_hub", "core_engine", "rag_engine", "scripts"]
    all_issues = []
    own_script = Path(__file__).resolve()
    
    for dirname in dirs:
        dirpath = Path(dirname)
        if not dirpath.exists():
            continue
        
        for pyfile in dirpath.rglob("*.py"):
            if pyfile.resolve() == own_script:
                continue  # 跳过自身
            
            issues = check_file(pyfile)
            if issues:
                all_issues.append(f"\n{pyfile}:")
                all_issues.extend(issues)
    
    if all_issues:
        print("发现假成功路径:")
        print("\n".join(all_issues))
        return 1
    
    print("通过: 未发现 mock/fake/dummy/default_success/fallback_success/default_pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())