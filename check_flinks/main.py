# check_flinks/main.py
# author:  ByteWyrm
# date: 2025.5.25 1:20
# TODO: 检测所有提供的友链链接:link、avator、friends-html、friends-rss、friends-repo
# Done：已经实现检测json部分链接状态并生成报告：link、avator
import os
import json
import time
import requests
from github import Github,GithubException
from concurrent.futures import ThreadPoolExecutor
import re

# 配置文件路径
STATUS_FILE = "link_status.json"

def parse_all_links(issue_body):
    """从 Issue 正文中提取友链列表"""
    links = []
    link_types = {}
    rss_link = None
    repo_link = None
    friends_html = None

    # --------------------------
    # 解析 JSON 部分（link, avatar）
    # --------------------------
    json_match = re.search(r'```json\s*({[\s\S]*?})\s*```', issue_body)
    if json_match:
        try:
            config = json.loads(json_match.group(1))
            if config.get("link"):
                links.append(config["link"])
                link_types[config["link"]] = "link"
            if config.get("avatar"):
                links.append(config["avatar"])
                link_types[config["avatar"]] = "avatar"
        except json.JSONDecodeError:
            pass

    # --------------------------
    # 解析友链地址（friends-html，必填）
    # --------------------------
    # 修正正则表达式，匹配 GitHub 渲染后的 HTML 结构
    html_match = re.search(
        r'name="friends-html"[^>]*value="([^"]+)"',  # 匹配 name 属性
        issue_body
    )
    if html_match and html_match.group(1).strip():
        friends_html = html_match.group(1).strip()
        links.append(friends_html)
        link_types[friends_html] = "friends-html"

    # --------------------------
    # 解析订阅地址（friends-rss，可选）
    # --------------------------
    rss_match = re.search(
        r'name="friends-rss"[^>]*value="([^"]+)"',
        issue_body
    )
    if rss_match and rss_match.group(1).strip():
        rss_link = rss_match.group(1).strip()
        links.append(rss_link)
        link_types[rss_link] = "rss"

    # --------------------------
    # 解析友链仓库（friends-repo，可选）
    # --------------------------
    repo_match = re.search(
        r'name="friends-repo"[^>]*value="([^"]+)"',
        issue_body
    )
    if repo_match and repo_match.group(1).strip():
        repo_link = repo_match.group(1).strip()
        links.append(repo_link)
        link_types[repo_link] = "repo"

    # --------------------------
    # 处理可选字段未填写的情况
    # --------------------------
    if not rss_link:
        links.append("未提供")
        link_types["未提供"] = "rss"
    if not repo_link:
        links.append("未提供")
        link_types["未提供"] = "repo"

    return links, link_types

def parse_links(issue_body):
    """从 Issue 正文中提取友链列表"""
    links = []
    link_types = {}

    # 解析 JSON 部分（link, avatar）
    json_match = re.search(r'```json\s*({[\s\S]*?})\s*```', issue_body)
    if json_match:
        try:
            config = json.loads(json_match.group(1))
            if config.get("link"):
                links.append(config["link"])
                link_types[config["link"]] = "link"
            if config.get("avatar"):
                links.append(config["avatar"])
                link_types[config["avatar"]] = "avatar"
        except json.JSONDecodeError:
            pass

    return links, link_types

def check_link(url, test_count=5):
    """检测单个链接状态，测试多次"""
    if url == "未提供":
        return {
            "url": url,
            "status": "未提供",
            "status_code": "N/A",
            "avg_latency": 0,
            "success_count": 0,
            "fail_count": 0,
            "success": True,  # 标记为成功以简化统计
            "error": None,
            "last_check": time.strftime('%Y-%m-%d %H:%M:%S')
        }

    results = []
    for _ in range(test_count):
        try:
            start_time = time.time()
            response = requests.get(
                url,
                timeout=10,
                allow_redirects=True,
                verify=True,
                headers={"User-Agent": "Mozilla/5.0 (GitHub Friend Link Checker)"}
            )
            latency = round(time.time() - start_time, 2)
            results.append({
                "status_code": response.status_code,
                "latency": latency,
                "success": response.ok,
                "error": None
            })
        except Exception as e:
            results.append({
                "status_code": "Error",
                "latency": 0,
                "success": False,
                "error": str(e)
            })

    # 计算成功率和平均延迟
    success_count = sum(1 for res in results if res["success"])
    fail_count = test_count - success_count
    avg_latency = round(sum(res["latency"] for res in results) / max(1, len(results)), 2)

    # 确定最终状态
    final_status = "可连接" if fail_count < 3 else "无法连接"
    status_code = results[-1]["status_code"] if results else "Unknown"

    return {
        "url": url,
        "status": final_status,
        "status_code": status_code,
        "avg_latency": avg_latency,
        "success_count": success_count,
        "fail_count": fail_count,
        "success": fail_count < 3,
        "error": next((res["error"] for res in results if res["error"]), None),
        "last_check": time.strftime('%Y-%m-%d %H:%M:%S')
    }

def load_status():
    """加载历史状态数据"""
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r") as f:
            return json.load(f)
    return {}

def update_status(results, link_types):
    """更新状态数据（成功次数/失败次数）"""
    status = load_status()
    for res in results:
        key = res["url"]
        if key not in status:
            status[key] = {
                "success": 0, 
                "fail": 0, 
                "type": link_types.get(key, "unknown"),
                "last_check": res["last_check"]
            }
        if res["success"]:
            status[key]["success"] += 1
        else:
            status[key]["fail"] += 1
        status[key]["last_check"] = res["last_check"]
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)
    return status

def generate_report(results, status, link_types):
    """生成优化的 Markdown 报告"""
    # 统计成功、失败、未提供的链接数量
    success_count = sum(1 for res in results if res["success"] and res["url"] != "未提供")
    fail_count = sum(1 for res in results if not res["success"] and res["url"] != "未提供")
    optional_missing = sum(1 for res in results if res["url"] == "未提供")
    
    report = [
        f"# 友链状态检测报告",
        f"**检测时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**检测结果**: 共检测 {len(results)} 个链接，{success_count} 个成功，{fail_count} 个失败，{optional_missing} 个未提供",
        ""
    ]
    
    # 需要修复的链接（排除未提供的链接）
    if fail_count > 0:
        report.append("## ⚠️ 需要修复的链接")
        report.append("| URL | 类型 | 状态 | 平均延迟 | 错误信息 |")
        report.append("|-----|------|------|----------|---------|")
        for res in results:
            if not res["success"] and res["url"] != "未提供":
                link_type = link_types.get(res["url"], "未知")
                error_msg = res.get("error", "无") or "无"
                row = f"| {res['url']} | {link_type} | {res['status']} | {res['avg_latency']}s | {error_msg} |"
                report.append(row)
        report.append("")
    
    # 所有链接状态（包含未提供的链接）
    report.append("## 所有链接状态")
    report.append("| URL | 类型 | 状态 | 平均延迟 | 成功次数 | 失败次数 | 最后检测时间 |")
    report.append("|-----|------|------|----------|---------|---------|--------------|")
    for res in results:
        key = res["url"]
        link_type = link_types.get(key, "未知")
        stats = status.get(key, {"success": 0, "fail": 0, "last_check": "无记录"})
        
        if key == "未提供":
            row = f"| {key} | {link_type} | 🟡 未提供 | - | - | - | - |"
        else:
            status_emoji = "✅" if res["success"] else "❌"
            total_success = stats["success"]
            total_fail = stats["fail"]
            last_check = stats["last_check"]
            row = f"| {key} | {link_type} | {status_emoji} {res['status']} | {res['avg_latency']}s | {total_success} | {total_fail} | {last_check} |"
        report.append(row)
    
    # 添加提示信息
    if fail_count > 0:
        report.append("\n⚠️ **有链接检测失败，请修复后重新提交**")
    else:
        report.append("\n✅ **所有链接检测通过**")
    
    return "\n".join(report)

def manage_labels(issue_number, is_success):
    """管理 Issue 标签"""
    try:
        g = Github(os.getenv("GITHUB_TOKEN"))
        repo = g.get_repo(os.getenv("GITHUB_REPOSITORY"))
        issue = repo.get_issue(issue_number)
        
        # 获取当前所有标签名称
        current_labels = [label.name for label in issue.labels]
        
        # 清理旧标签（仅删除存在的标签）
        for label in ["active", "needs-fix"]:
            if label in current_labels:
                issue.remove_from_labels(label)
        
        # 添加新标签
        new_label = "active" if is_success else "needs-fix"
        issue.add_to_labels(new_label)
    except GithubException as e:
        if e.status == 410:
            print(f"⚠️ Issue #{issue_number} 已被删除，跳过标签操作。")
        else:
            raise

if __name__ == "__main__":
    # 从环境变量获取 Issue 数据
    issue_body = os.getenv("ISSUE_BODY")
    issue_number = int(os.getenv("ISSUE_NUMBER"))

    # 提取并检测链接
    links, link_types = parse_links(issue_body)
    results = []

    for link in links:
        results.append(check_link(link, test_count=5))
    
    # 标签管理
    all_success = all(res["success"] for res in results)
    manage_labels(issue_number, all_success)

    # 更新状态并生成报告
    status = update_status(results, link_types)
    report = generate_report(results, status, link_types)
    
    # 输出报告到 Artifact 并评论
    with open("link_report.md", "w") as f:
        f.write(report)