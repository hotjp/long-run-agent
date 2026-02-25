#!/usr/bin/env python3
"""
LRA v3.2.1 性能基准测试

测试场景：
1. 单任务操作（创建/读取/更新/删除）
2. 并发任务操作（多进程模拟多 Agent）
3. 依赖关系解锁性能
4. 大数据量压力测试

性能指标：
- 内存占用（MB）
- 操作延迟（ms）
- 吞吐量（ops/s）
- I/O 读写（KB/s）
"""

import os
import sys
import json
import time
import shutil
import tempfile
import multiprocessing as mp
from datetime import datetime
from typing import Dict, Any, List, Tuple
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("⚠️  警告：psutil 未安装，内存监控将不可用")
    print("   安装：pip install psutil")

from long_run_agent.task_manager import TaskManager
from long_run_agent.locks_manager import LocksManager
from long_run_agent.template_manager import TemplateManager
from long_run_agent.config import Config, SafeJson


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.process = psutil.Process() if HAS_PSUTIL else None
        self.start_time = None
        self.io_read_count = 0
        self.io_write_count = 0
        self.io_read_bytes = 0
        self.io_write_bytes = 0
        self.operations = []
    
    def start(self):
        """开始监控"""
        self.start_time = time.time()
        if self.process:
            self.process.cpu_percent()  # 初始化 CPU 测量
        return self
    
    def stop(self):
        """停止监控"""
        self.end_time = time.time()
        return self
    
    def record_operation(self, op_type: str, duration: float, data_size: int = 0):
        """记录一次操作"""
        self.operations.append({
            "type": op_type,
            "duration": duration,
            "data_size": data_size,
            "timestamp": time.time()
        })
        if data_size > 0:
            if "read" in op_type.lower() or "load" in op_type.lower():
                self.io_read_count += 1
                self.io_read_bytes += data_size
            elif "write" in op_type.lower() or "save" in op_type.lower():
                self.io_write_count += 1
                self.io_write_bytes += data_size
    
    def get_memory_mb(self) -> float:
        """获取当前内存占用（MB）"""
        if self.process:
            return self.process.memory_info().rss / 1024 / 1024
        return 0.0
    
    def get_cpu_percent(self) -> float:
        """获取 CPU 使用率"""
        if self.process:
            return self.process.cpu_percent()
        return 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.start_time or not self.end_time:
            return {}
        
        duration = self.end_time - self.start_time
        total_ops = len(self.operations)
        
        # 计算平均延迟
        avg_latency = 0
        if self.operations:
            avg_latency = sum(op["duration"] for op in self.operations) / len(self.operations) * 1000  # ms
        
        # 计算吞吐量
        throughput = total_ops / duration if duration > 0 else 0
        
        # I/O 统计
        io_read_kb = self.io_read_bytes / 1024
        io_write_kb = self.io_write_bytes / 1024
        io_throughput = (io_read_kb + io_write_kb) / duration if duration > 0 else 0
        
        return {
            "duration_seconds": round(duration, 2),
            "total_operations": total_ops,
            "avg_latency_ms": round(avg_latency, 2),
            "throughput_ops_per_sec": round(throughput, 2),
            "io_reads": self.io_read_count,
            "io_writes": self.io_write_count,
            "io_read_kb": round(io_read_kb, 2),
            "io_write_kb": round(io_write_kb, 2),
            "io_throughput_kb_per_sec": round(io_throughput, 2),
        }


class IOTracer:
    """I/O 追踪器 - 包装 SafeJson 来统计 I/O"""
    
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
        self.original_read = SafeJson.read
        self.original_write = SafeJson.write
        self._install_tracer()
    
    def _install_tracer(self):
        """安装 I/O 追踪器"""
        def traced_read(path: str):
            start = time.time()
            result = self.original_read(path)
            duration = time.time() - start
            
            # 计算文件大小
            size = 0
            if os.path.exists(path):
                size = os.path.getsize(path)
            
            self.monitor.record_operation("json_read", duration, size)
            return result
        
        def traced_write(path: str, data: Dict[str, Any]) -> bool:
            start = time.time()
            result = self.original_write(path, data)
            duration = time.time() - start
            
            # 估算写入大小
            size = len(json.dumps(data).encode('utf-8'))
            
            self.monitor.record_operation("json_write", duration, size)
            return result
        
        SafeJson.read = traced_read
        SafeJson.write = traced_write
    
    def uninstall(self):
        """卸载追踪器"""
        SafeJson.read = self.original_read
        SafeJson.write = self.original_write


def create_test_environment(test_dir: str) -> str:
    """创建测试环境"""
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)
    os.chdir(test_dir)
    
    # 初始化项目
    tm = TaskManager()
    tm.init_project("Performance Test")
    
    return test_dir


def cleanup_test_environment(test_dir: str):
    """清理测试环境"""
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)


def benchmark_single_task(monitor: PerformanceMonitor, num_tasks: int) -> Dict[str, Any]:
    """单任务操作基准测试"""
    tm = TaskManager()
    
    results = {
        "create_times": [],
        "read_times": [],
        "update_times": [],
    }
    
    # 创建任务
    for i in range(num_tasks):
        start = time.time()
        success, task = tm.create(
            description=f"Performance test task {i}",
            template="task",
            priority="P1",
            output_req="8k"
        )
        duration = time.time() - start
        results["create_times"].append(duration)
    
    # 读取任务
    for i in range(num_tasks):
        task_id = f"task_{i+1:03d}"
        start = time.time()
        task = tm.get(task_id)
        duration = time.time() - start
        results["read_times"].append(duration)
    
    # 更新任务状态
    for i in range(num_tasks):
        task_id = f"task_{i+1:03d}"
        start = time.time()
        tm.update_status(task_id, "in_progress")
        duration = time.time() - start
        results["update_times"].append(duration)
    
    # 计算统计
    return {
        "create_avg_ms": round(sum(results["create_times"]) / len(results["create_times"]) * 1000, 2),
        "read_avg_ms": round(sum(results["read_times"]) / len(results["read_times"]) * 1000, 2),
        "update_avg_ms": round(sum(results["update_times"]) / len(results["update_times"]) * 1000, 2),
    }


def benchmark_concurrent_tasks(monitor: PerformanceMonitor, num_tasks: int, num_workers: int) -> Dict[str, Any]:
    """并发任务操作测试"""
    from multiprocessing import Pool
    
    tm = TaskManager()
    results = {"times": [], "success": 0, "failed": 0}
    
    def worker_task(task_id: int) -> Tuple[int, float, bool]:
        """工作进程"""
        try:
            local_tm = TaskManager()
            local_locks = LocksManager()
            
            # 创建任务
            start = time.time()
            success, task = local_tm.create(
                description=f"Concurrent task {task_id}",
                template="task",
                priority="P1"
            )
            
            if not success:
                return (task_id, time.time() - start, False)
            
            # Claim 任务
            local_locks.claim(task["id"])
            
            # 更新状态
            local_tm.update_status(task["id"], "in_progress")
            local_tm.update_status(task["id"], "completed")
            
            # Release
            local_locks.release(task["id"])
            
            return (task_id, time.time() - start, True)
        except Exception as e:
            return (task_id, 0, False)
    
    # 使用进程池并发执行
    with Pool(processes=num_workers) as pool:
        task_ids = range(num_tasks)
        task_results = list(pool.imap(worker_task, task_ids))
    
    for task_id, duration, success in task_results:
        results["times"].append(duration)
        if success:
            results["success"] += 1
        else:
            results["failed"] += 1
    
    return {
        "total_tasks": num_tasks,
        "success": results["success"],
        "failed": results["failed"],
        "avg_time_ms": round(sum(results["times"]) / len(results["times"]) * 1000, 2) if results["times"] else 0,
        "total_time_sec": round(sum(results["times"]), 2),
    }


def benchmark_dependencies(monitor: PerformanceMonitor, num_tasks: int, dependency_depth: int) -> Dict[str, Any]:
    """依赖关系性能测试"""
    tm = TaskManager()
    
    results = {
        "create_with_deps_times": [],
        "unlock_times": [],
    }
    
    # 创建基础任务（无依赖）
    base_tasks = []
    for i in range(dependency_depth):
        start = time.time()
        success, task = tm.create(
            description=f"Base task {i}",
            priority="P1"
        )
        duration = time.time() - start
        base_tasks.append(task["id"])
    
    # 创建带依赖的任务
    for i in range(num_tasks):
        deps = base_tasks[:min(i+1, dependency_depth)]
        start = time.time()
        success, task = tm.create(
            description=f"Dependent task {i}",
            dependencies=deps,
            dependency_type="all"
        )
        duration = time.time() - start
        results["create_with_deps_times"].append(duration)
    
    # 完成基础任务，触发解锁
    start = time.time()
    for task_id in base_tasks:
        tm.update_status(task_id, "completed")
    unlock_duration = time.time() - start
    
    # 检查 blocked 任务
    start = time.time()
    unblocked = tm.check_blocked_tasks()
    check_duration = time.time() - start
    
    return {
        "create_with_deps_avg_ms": round(sum(results["create_with_deps_times"]) / len(results["create_with_deps_times"]) * 1000, 2),
        "unlock_duration_ms": round(unlock_duration * 1000, 2),
        "check_duration_ms": round(check_duration * 1000, 2),
        "unblocked_count": unblocked,
    }


def run_benchmark_suite():
    """运行完整的性能测试套件"""
    print("=" * 70)
    print("LRA v3.2.1 性能基准测试")
    print("=" * 70)
    print()
    
    test_dir = tempfile.mkdtemp(prefix="lra_benchmark_")
    print(f"📁 测试目录：{test_dir}")
    print()
    
    all_results = []
    
    # 测试规模配置
    test_scales = [10, 50, 100, 200, 500, 1000]
    
    for scale in test_scales:
        print(f"🔍 测试规模：{scale} 任务")
        print("-" * 70)
        
        # 创建干净的测试环境
        scale_dir = os.path.join(test_dir, f"scale_{scale}")
        create_test_environment(scale_dir)
        
        # 创建监控器
        monitor = PerformanceMonitor()
        io_tracer = IOTracer(monitor)
        
        try:
            # 开始监控
            monitor.start()
            initial_memory = monitor.get_memory_mb()
            
            # 1. 单任务基准测试
            single_task_results = benchmark_single_task(monitor, scale)
            
            # 2. 依赖关系测试（只对较小规模执行完整测试）
            if scale <= 200:
                deps_results = benchmark_dependencies(monitor, min(scale, 50), min(scale, 10))
            else:
                deps_results = {
                    "create_with_deps_avg_ms": "N/A",
                    "unlock_duration_ms": "N/A",
                    "check_duration_ms": "N/A",
                    "unblocked_count": "N/A",
                }
            
            # 停止监控
            monitor.stop()
            final_memory = monitor.get_memory_mb()
            stats = monitor.get_stats()
            
            # 计算结果
            memory_increase = final_memory - initial_memory
            memory_per_task = memory_increase / scale * 1024 if scale > 0 else 0  # KB
            
            result = {
                "scale": scale,
                "memory_base_mb": round(initial_memory, 2),
                "memory_peak_mb": round(final_memory, 2),
                "memory_per_task_kb": round(memory_per_task, 2),
                "create_avg_ms": single_task_results["create_avg_ms"],
                "read_avg_ms": single_task_results["read_avg_ms"],
                "update_avg_ms": single_task_results["update_avg_ms"],
                "throughput_ops_per_sec": stats["throughput_ops_per_sec"],
                "io_read_kb": stats["io_read_kb"],
                "io_write_kb": stats["io_write_kb"],
                "io_throughput_kb_per_sec": stats["io_throughput_kb_per_sec"],
                "deps_create_avg_ms": deps_results.get("create_with_deps_avg_ms", "N/A"),
                "test_timestamp": datetime.now().isoformat(),
            }
            
            all_results.append(result)
            
            # 打印结果
            print(f"   内存占用：{initial_memory:.2f} MB → {final_memory:.2f} MB")
            print(f"   每任务内存：{memory_per_task:.2f} KB")
            print(f"   创建延迟：{single_task_results['create_avg_ms']:.2f} ms")
            print(f"   读取延迟：{single_task_results['read_avg_ms']:.2f} ms")
            print(f"   更新延迟：{single_task_results['update_avg_ms']:.2f} ms")
            print(f"   吞吐量：{stats['throughput_ops_per_sec']:.2f} ops/s")
            print(f"   I/O 读取：{stats['io_read_kb']:.2f} KB")
            print(f"   I/O 写入：{stats['io_write_kb']:.2f} KB")
            if scale <= 200:
                print(f"   依赖创建：{deps_results['create_with_deps_avg_ms']:.2f} ms")
            print()
            
        except Exception as e:
            print(f"   ❌ 测试失败：{e}")
            import traceback
            traceback.print_exc()
            print()
        
        finally:
            io_tracer.uninstall()
    
    # 清理测试环境
    cleanup_test_environment(test_dir)
    
    return all_results


def generate_markdown_table(results: List[Dict[str, Any]]) -> str:
    """生成 Markdown 表格"""
    lines = []
    
    lines.append("## 性能基准测试")
    lines.append("")
    lines.append(f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("### 测试环境")
    lines.append("")
    lines.append(f"- **Python**: {sys.version.split()[0]}")
    lines.append(f"- **操作系统**: {sys.platform}")
    lines.append(f"- **CPU 核心数**: {mp.cpu_count()}")
    if HAS_PSUTIL:
        lines.append(f"- **物理内存**: {round(psutil.virtual_memory().total / 1024 / 1024 / 1024, 2)} GB")
    lines.append("")
    
    lines.append("### 性能指标")
    lines.append("")
    lines.append("| 规模 | 基础内存 (MB) | 峰值内存 (MB) | 每任务内存 (KB) | 创建延迟 (ms) | 读取延迟 (ms) | 更新延迟 (ms) | 吞吐量 (ops/s) | I/O 读取 (KB) | I/O 写入 (KB) | I/O 吞吐 (KB/s) |")
    lines.append("|------|---------------|---------------|-----------------|---------------|---------------|---------------|----------------|---------------|---------------|-----------------|")
    
    for r in results:
        deps_note = "⚡" if r["deps_create_avg_ms"] != "N/A" else ""
        lines.append(
            f"| {r['scale']} {deps_note} | "
            f"{r['memory_base_mb']} | "
            f"{r['memory_peak_mb']} | "
            f"{r['memory_per_task_kb']} | "
            f"{r['create_avg_ms']} | "
            f"{r['read_avg_ms']} | "
            f"{r['update_avg_ms']} | "
            f"{r['throughput_ops_per_sec']} | "
            f"{r['io_read_kb']} | "
            f"{r['io_write_kb']} | "
            f"{r['io_throughput_kb_per_sec']} |"
        )
    
    lines.append("")
    lines.append("**说明**:")
    lines.append("- ⚡ 表示执行了依赖关系测试（200 任务以下）")
    lines.append("- 测试使用临时目录，完成后自动清理")
    lines.append("- 每个规模测试包含：创建、读取、更新操作")
    lines.append("")
    
    # 性能分析
    lines.append("### 性能分析")
    lines.append("")
    
    if results:
        # 内存增长分析
        if len(results) >= 2:
            small = results[0]
            large = results[-1]
            memory_growth = (large["memory_peak_mb"] - small["memory_peak_mb"]) / small["memory_peak_mb"] * 100
            lines.append(f"- **内存增长**: {small['scale']} 任务 → {large['scale']} 任务，内存增长 {memory_growth:.1f}%")
        
        # 延迟分析
        lines.append(f"- **平均创建延迟**: {sum(r['create_avg_ms'] for r in results if isinstance(r['create_avg_ms'], (int, float))) / len([r for r in results if isinstance(r['create_avg_ms'], (int, float))]):.2f} ms")
        lines.append(f"- **平均读取延迟**: {sum(r['read_avg_ms'] for r in results if isinstance(r['read_avg_ms'], (int, float))) / len([r for r in results if isinstance(r['read_avg_ms'], (int, float))]):.2f} ms")
        lines.append(f"- **平均更新延迟**: {sum(r['update_avg_ms'] for r in results if isinstance(r['update_avg_ms'], (int, float))) / len([r for r in results if isinstance(r['update_avg_ms'], (int, float))]):.2f} ms")
        lines.append("")
        
        # 性能评级
        lines.append("### 性能评级")
        lines.append("")
        avg_throughput = sum(r['throughput_ops_per_sec'] for r in results if isinstance(r['throughput_ops_per_sec'], (int, float))) / len([r for r in results if isinstance(r['throughput_ops_per_sec'], (int, float))])
        if avg_throughput > 500:
            lines.append("🟢 **优秀**: 系统性能优秀，适合大规模任务管理")
        elif avg_throughput > 200:
            lines.append("🟡 **良好**: 系统性能良好，适合中等规模任务管理")
        else:
            lines.append("🔴 **一般**: 系统性能一般，建议优化或减少任务规模")
        lines.append("")
    
    return "\n".join(lines)


def main():
    """主函数"""
    print("=" * 70)
    print("LRA v3.2.1 性能基准测试")
    print("=" * 70)
    print()
    
    # 检查依赖
    if not HAS_PSUTIL:
        print("⚠️  警告：psutil 未安装")
        print("   部分性能指标将不可用")
        print("   建议安装：pip install psutil")
        print()
        response = input("是否继续测试？(y/n): ")
        if response.lower() != 'y':
            print("测试取消")
            return
    
    print("🚀 开始性能测试...")
    print("   这可能需要几分钟时间，请耐心等待")
    print()
    
    # 运行测试
    results = run_benchmark_suite()
    
    if not results:
        print("❌ 测试失败，没有生成结果")
        return
    
    # 生成报告
    print()
    print("=" * 70)
    print("生成测试报告...")
    print("=" * 70)
    print()
    
    markdown = generate_markdown_table(results)
    
    # 保存结果
    output_dir = Path(__file__).parent
    report_file = output_dir / "BENCHMARK_RESULTS.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(markdown)
    
    print(f"✅ 测试报告已保存至：{report_file}")
    print()
    
    # 保存 JSON 数据
    json_file = output_dir / "benchmark_results.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 原始数据已保存至：{json_file}")
    print()
    
    # 打印摘要
    print("=" * 70)
    print("性能测试摘要")
    print("=" * 70)
    print()
    
    for r in results:
        print(f"规模 {r['scale']:4d} 任务: "
              f"内存 {r['memory_peak_mb']:6.2f} MB, "
              f"创建 {r['create_avg_ms']:6.2f} ms, "
              f"吞吐 {r['throughput_ops_per_sec']:6.2f} ops/s")
    
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
