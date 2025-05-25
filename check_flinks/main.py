# check_flinks/main.py
# author: ByteWyrm
# date: 2025.5.25 1:20
import os
import re
import json
import time
from datetime import datetime
from github import Github
import requests

def parse_issue_body(body):
    """解析Issue中的JSON配置"""
    match = re.search(r'```json\s*(.*?)\s*```', body, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None

class LinkTester:
    """链接测试器"""
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }

    def test_endpoint(self, url):
        """执行5次测试并返回详细结果"""
        results = []
        total_delay = 0
        success_count = 0
        
        for _ in range(5):
            start_time = time.time()
            try:
                response = self.session.get(
                    url,
                    timeout=10,
                    headers=self.headers
                )
                delay = round(time.time() - start_time, 2)
                if response.status_code == 200:
                    success_count += 1
                    results.append(("✅ 成功", delay))
                else:
                    results.append(("❌ 失败", delay))
            except Exception:
                delay = round(time.time() - start_time, 2)
                results.append(("❌ 异常", delay))
            total_delay += delay
            time.sleep(1)  # 间隔防止高频请求

        return {
            "url": url,
            "results": results,
            "success_count": success_count,
            "avg_delay": round(total_delay/5, 2),
            "last_test": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

def generate_md_report(link_data, avatar_data):
    """生成Markdown格式检测报告"""
    # 汇总统计
    total_tests = 2
    success_tests = 0
    if link_data['success_count'] >=3: success_tests +=1
    if avatar_data['success_count'] >=3: success_tests +=1
    
    # 表格生成
    table_rows = []
    for data in [link_data, avatar_data]:
        row = [
            data['url'],
            'link' if data is link_data else 'avatar',
            '✅ 可连接' if data['success_count'] >=3 else '❌ 不可达',
            f"{data['avg_delay']}s",
            data['success_count'],
            5 - data['success_count'],
            data['last_test']
        ]
        table_rows.append("| " + " | ".join(map(str, row)) + " |")
    
    return f"""# 友链状态检测报告
**检测时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**检测结果**: 共检测 {total_tests} 个链接，{success_tests} 个成功，{total_tests-success_tests} 个失败

## 所有链接状态
| URL | 类型 | 状态 | 平均延迟 | 成功次数 | 失败次数 | 最后检测时间 |
|-----|------|------|----------|---------|---------|--------------|
{chr(10).join(table_rows)}

{"✅ **所有链接检测通过**" if success_tests == total_tests else "❌ **存在不可达链接**"}"""

def update_labels(issue, is_all_ok):
    """更新Issue标签"""
    target_label = "activate" if is_all_ok else "needs-fix"
    labels_to_remove = ["activate", "needs-fix"]
    
    # 移除冲突标签
    for label in issue.labels:
        if label.name in labels_to_remove and label.name != target_label:
            issue.remove_from_labels(label.name)
    
    # 添加新标签
    if not any(label.name == target_label for label in issue.labels):
        issue.add_to_labels(target_label)

def main():
    # 获取环境变量
    issue_body = os.getenv('ISSUE_BODY')
    gh_token = os.getenv('GITHUB_TOKEN')
    repo_name = os.getenv('GITHUB_REPOSITORY')
    issue_num = int(os.getenv('ISSUE_NUMBER'))
    
    if not all([issue_body, gh_token, repo_name, issue_num]):
        print("缺少必要环境变量")
        return

    # 解析配置
    config = parse_issue_body(issue_body)
    if not config or 'link' not in config or 'avatar' not in config:
        print("无效的友链配置")
        return

    # 执行检测
    tester = LinkTester()
    link_result = tester.test_endpoint(config['link'])
    avatar_result = tester.test_endpoint(config['avatar'])
    
    # 生成报告
    report_content = generate_md_report(link_result, avatar_result)
    
    # 连接GitHub
    g = Github(gh_token)
    repo = g.get_repo(repo_name)
    issue = repo.get_issue(issue_num)
    
    # 发布报告
    existing_comments = issue.get_comments()
    for comment in existing_comments:
        if "友链状态检测报告" in comment.body:
            comment.edit(report_content)
            break
    else:
        issue.create_comment(report_content)
    
    # 更新标签
    update_labels(issue, (link_result['success_count'] >=3) and (avatar_result['success_count'] >=3))

if __name__ == "__main__":
    main()