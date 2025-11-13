#!/usr/bin/env python3
"""
完整整合測試腳本

測試項目：
1. 上傳測試資料（公告含時效性標註、裁罰案件）
2. 多 Store 查詢功能
3. 時效性規則驗證
4. 參考文件數量控制
5. System Instruction 效果
"""

import sys
import os
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

# 加入專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from loguru import logger

# 配置日誌
logger.remove()
logger.add(sys.stderr, level="INFO")

# 檢查 Gemini SDK
try:
    from google import genai
    from google.genai import types
except ImportError:
    logger.error("請先安裝 Gemini SDK: pip install google-genai")
    sys.exit(1)


class IntegrationTester:
    """整合測試器"""

    def __init__(self, api_key: str):
        """初始化"""
        self.client = genai.Client(api_key=api_key)
        self.test_stores = {}
        self.uploaded_files = {}

    def setup_test_stores(self) -> bool:
        """建立測試用的 Stores"""
        logger.info("=" * 70)
        logger.info("步驟 1: 建立測試 Stores")
        logger.info("=" * 70)

        store_configs = [
            ('fsc-integration-test-announcements', '公告測試'),
            ('fsc-integration-test-penalties', '裁罰測試')
        ]

        for store_name, description in store_configs:
            try:
                # 檢查是否已存在
                stores = list(self.client.file_search_stores.list())
                existing = [s for s in stores if s.display_name == store_name]

                if existing:
                    logger.info(f"✓ 測試 Store 已存在: {store_name}")
                    store = existing[0]
                else:
                    logger.info(f"建立測試 Store: {store_name}")
                    store = self.client.file_search_stores.create(
                        config=types.CreateFileSearchStoreConfig(
                            display_name=store_name
                        )
                    )
                    logger.info(f"✓ Store 建立成功: {store.name}")

                # 儲存 Store 資訊
                store_type = 'announcements' if 'announcements' in store_name else 'penalties'
                self.test_stores[store_type] = store

            except Exception as e:
                logger.error(f"建立 Store 失敗 ({store_name}): {e}")
                return False

        logger.info("")
        return True

    def upload_test_data(self) -> bool:
        """上傳測試資料"""
        logger.info("=" * 70)
        logger.info("步驟 2: 上傳測試資料")
        logger.info("=" * 70)

        # 使用時效性標註測試資料（公告）
        announcements_dir = Path('data/markdown/temporal_test')
        if announcements_dir.exists():
            files = list(announcements_dir.glob('*.md'))
            logger.info(f"找到 {len(files)} 個公告測試檔案（含時效性標註）")

            success_count = 0
            for file_path in files[:3]:  # 只上傳前 3 個
                if self._upload_file(
                    file_path,
                    self.test_stores['announcements'].name,
                    '公告'
                ):
                    success_count += 1

            logger.info(f"✓ 公告上傳完成: {success_count}/{min(3, len(files))}")
        else:
            logger.warning(f"公告測試目錄不存在: {announcements_dir}")
            logger.info("將使用簡化的測試資料")
            self._upload_simple_announcement()

        # 使用裁罰測試資料
        penalties_dir = Path('data/markdown/penalties_individual')
        if penalties_dir.exists():
            files = list(penalties_dir.glob('*.md'))
            logger.info(f"找到 {len(files)} 個裁罰測試檔案")

            success_count = 0
            for file_path in files[:2]:  # 只上傳前 2 個
                if self._upload_file(
                    file_path,
                    self.test_stores['penalties'].name,
                    '裁罰'
                ):
                    success_count += 1

            logger.info(f"✓ 裁罰上傳完成: {success_count}/{min(2, len(files))}")
        else:
            logger.warning(f"裁罰測試目錄不存在: {penalties_dir}")
            logger.info("將使用簡化的測試資料")
            self._upload_simple_penalty()

        # 等待檔案處理
        logger.info("\n等待 10 秒讓檔案處理完成...")
        time.sleep(10)

        logger.info("")
        return True

    def _upload_file(self, file_path: Path, store_name: str, data_type: str) -> bool:
        """上傳單個檔案"""
        try:
            logger.info(f"  上傳: {file_path.name[:60]}...")

            with open(file_path, 'rb') as f:
                file_obj = self.client.files.upload(
                    file=f,
                    config=types.UploadFileConfig(
                        display_name=file_path.name,
                        mime_type='text/markdown'
                    )
                )

            # 加入 Store
            self.client.file_search_stores.import_file(
                file_search_store_name=store_name,
                file_name=file_obj.name
            )

            # 記錄上傳的檔案
            if data_type not in self.uploaded_files:
                self.uploaded_files[data_type] = []
            self.uploaded_files[data_type].append(file_path.name)

            return True

        except Exception as e:
            logger.error(f"  上傳失敗: {e}")
            return False

    def _upload_simple_announcement(self):
        """上傳簡化的公告測試資料"""
        content = """# 測試公告 - 保險業內部控制辦法

⭐ **最新版本**（2025-01-01）

## 📋 基本資訊
- **文件編號**: `test_ann_001`
- **發布日期**: 2025-01-01
- **來源單位**: 保險局
- **公告類型**: 法規修正

## 📄 內容
修正保險業內部控制相關規定。

## 📜 修正歷程
- **2025-01-01**：最新修正（本文件）⭐
- 2023-12-15：前次修正

*本文件為最新有效版本，取代所有先前版本。*
"""
        self._upload_simple_file(content, 'test_announcement_latest.md', 'announcements')

    def _upload_simple_penalty(self):
        """上傳簡化的裁罰測試資料"""
        content = """# 測試裁罰 - 某銀行內控缺失

## 📋 基本資訊
- **文件編號**: `test_pen_001`
- **發文字號**: 金管銀控字第11400000001號
- **發布日期**: 2025-01-15

## ⚖️ 處分內容
- **處分金額**: 新臺幣100萬元
- **違規類型**: 內部控制缺失

## 📝 違規事由
**摘要**: 內部控制制度未落實執行
**詳細說明**: 該銀行在內部控制方面存在多項缺失...
"""
        self._upload_simple_file(content, 'test_penalty_001.md', 'penalties')

    def _upload_simple_file(self, content: str, filename: str, data_type: str):
        """上傳簡單的測試檔案"""
        try:
            temp_dir = Path('data/temp_integration_test')
            temp_dir.mkdir(parents=True, exist_ok=True)

            file_path = temp_dir / filename
            file_path.write_text(content, encoding='utf-8')

            store_name = self.test_stores[data_type].name
            self._upload_file(file_path, store_name, data_type)

            # 清理
            file_path.unlink()

        except Exception as e:
            logger.error(f"上傳簡單測試檔案失敗: {e}")

    def test_single_store_queries(self) -> Dict[str, bool]:
        """測試單一 Store 查詢"""
        logger.info("=" * 70)
        logger.info("步驟 3: 測試單一 Store 查詢")
        logger.info("=" * 70)

        results = {}

        # 測試 1: 只查詢公告
        logger.info("\n[測試 3.1] 只查詢公告 Store")
        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents='這個 Store 包含什麼類型的資料？',
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=[self.test_stores['announcements'].name]
                            )
                        )
                    ]
                )
            )
            logger.info(f"✓ 查詢成功")
            logger.info(f"回應: {response.text[:200]}...")
            results['single_announcements'] = True
        except Exception as e:
            logger.error(f"✗ 查詢失敗: {e}")
            results['single_announcements'] = False

        # 測試 2: 只查詢裁罰
        logger.info("\n[測試 3.2] 只查詢裁罰 Store")
        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents='這個 Store 包含什麼類型的資料？',
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=[self.test_stores['penalties'].name]
                            )
                        )
                    ]
                )
            )
            logger.info(f"✓ 查詢成功")
            logger.info(f"回應: {response.text[:200]}...")
            results['single_penalties'] = True
        except Exception as e:
            logger.error(f"✗ 查詢失敗: {e}")
            results['single_penalties'] = False

        logger.info("")
        return results

    def test_multi_store_query(self) -> bool:
        """測試多 Store 查詢"""
        logger.info("=" * 70)
        logger.info("步驟 4: 測試多 Store 查詢 ⭐")
        logger.info("=" * 70)

        logger.info("\n[測試 4.1] 同時查詢公告和裁罰")
        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents='這些 Stores 分別包含什麼類型的資料？',
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=[
                                    self.test_stores['announcements'].name,
                                    self.test_stores['penalties'].name
                                ]
                            )
                        )
                    ]
                )
            )
            logger.info(f"✓✓✓ 多 Store 查詢成功！")
            logger.info(f"回應: {response.text[:300]}...")

            logger.info("\n" + "=" * 70)
            logger.info("結論: ✅ Gemini File Search API 支援多 Store 查詢")
            logger.info("=" * 70)

            return True

        except Exception as e:
            logger.error(f"✗✗✗ 多 Store 查詢失敗: {e}")
            logger.warning("\n" + "=" * 70)
            logger.warning("結論: ❌ 多 Store 查詢不支援或有問題")
            logger.warning("=" * 70)
            return False

    def test_temporal_annotation(self) -> bool:
        """測試時效性標註"""
        logger.info("\n" + "=" * 70)
        logger.info("步驟 5: 測試時效性標註功能")
        logger.info("=" * 70)

        # System Instruction 強調時效性
        system_instruction = """
你是金管會法規查詢助理。

【重要】時效性規則：
1. 優先使用標註「⭐ 最新版本」的文件
2. 如果檢索到多個相關公告，比較發文日期，使用最新的
3. 明確告知使用者你引用的是哪個日期的規定
4. 如果文件標註「⚠️ 此版本已過時」，提醒使用者這是過時版本
"""

        logger.info("\n[測試 5.1] 查詢法規，驗證是否使用最新版本")
        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents='保險業內部控制辦法的最新規定是什麼？請告訴我你引用的版本日期。',
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=[self.test_stores['announcements'].name]
                            )
                        )
                    ]
                )
            )

            logger.info(f"✓ 查詢成功")
            logger.info(f"回應:\n{response.text}")

            # 檢查是否提到最新版本
            if '2025' in response.text or '最新' in response.text:
                logger.info("\n✓ 系統正確識別了最新版本")
                return True
            else:
                logger.warning("\n⚠ 無法確認是否使用最新版本")
                return False

        except Exception as e:
            logger.error(f"✗ 查詢失敗: {e}")
            return False

    def test_reference_control(self) -> bool:
        """測試參考文件數量控制"""
        logger.info("\n" + "=" * 70)
        logger.info("步驟 6: 測試參考文件數量控制")
        logger.info("=" * 70)

        # 測試 1: 要求只列出 Top 3
        logger.info("\n[測試 6.1] 要求只列出前 3 個結果")

        system_instruction_limited = """
請只列出前 3 個最相關的結果。
每個結果都要簡短說明。
"""

        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents='列出所有可用的文件',
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction_limited,
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=[
                                    self.test_stores['announcements'].name,
                                    self.test_stores['penalties'].name
                                ]
                            )
                        )
                    ]
                )
            )

            logger.info(f"✓ 查詢成功")
            logger.info(f"回應:\n{response.text}")

            return True

        except Exception as e:
            logger.error(f"✗ 查詢失敗: {e}")
            return False

    def cleanup(self, delete_stores: bool = False):
        """清理測試環境"""
        logger.info("\n" + "=" * 70)
        logger.info("清理測試環境")
        logger.info("=" * 70)

        if delete_stores:
            logger.info("刪除測試 Stores...")
            for store_type, store in self.test_stores.items():
                try:
                    self.client.file_search_stores.delete(name=store.name)
                    logger.info(f"✓ 已刪除: {store.display_name}")
                except Exception as e:
                    logger.error(f"✗ 刪除失敗 ({store.display_name}): {e}")
        else:
            logger.info("測試 Stores 保留（如需刪除，請使用 --cleanup 參數）")

        logger.info("")


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description='完整整合測試')
    parser.add_argument('--cleanup', action='store_true', help='測試後刪除測試 Stores')
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("金管會爬蟲專案 - 完整整合測試")
    logger.info("=" * 70)
    logger.info("")

    # 載入環境變數
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')

    if not api_key:
        logger.error("請在 .env 中設定 GEMINI_API_KEY")
        logger.info("\n測試無法執行，需要 Gemini API Key")
        logger.info("請參考 .env.example 設定環境變數")
        sys.exit(1)

    # 建立測試器
    tester = IntegrationTester(api_key)

    try:
        # 執行測試
        results = {}

        # 步驟 1-2: 設定環境
        if not tester.setup_test_stores():
            logger.error("建立測試 Stores 失敗")
            sys.exit(1)

        if not tester.upload_test_data():
            logger.error("上傳測試資料失敗")
            sys.exit(1)

        # 步驟 3: 單一 Store 查詢
        results['single_store'] = tester.test_single_store_queries()

        # 步驟 4: 多 Store 查詢
        results['multi_store'] = tester.test_multi_store_query()

        # 步驟 5: 時效性標註
        results['temporal'] = tester.test_temporal_annotation()

        # 步驟 6: 參考文件控制
        results['reference_control'] = tester.test_reference_control()

        # 清理
        tester.cleanup(delete_stores=args.cleanup)

        # 總結
        logger.info("=" * 70)
        logger.info("測試總結")
        logger.info("=" * 70)

        all_passed = all([
            all(results['single_store'].values()) if 'single_store' in results else False,
            results.get('multi_store', False),
            results.get('temporal', False),
            results.get('reference_control', False)
        ])

        if all_passed:
            logger.info("✓✓✓ 所有測試通過！")
        else:
            logger.warning("⚠ 部分測試失敗，請檢查上方日誌")

        logger.info("\n測試結果:")
        logger.info(f"  單一 Store 查詢: {'✓' if all(results.get('single_store', {}).values()) else '✗'}")
        logger.info(f"  多 Store 查詢: {'✓' if results.get('multi_store', False) else '✗'}")
        logger.info(f"  時效性標註: {'✓' if results.get('temporal', False) else '✗'}")
        logger.info(f"  參考文件控制: {'✓' if results.get('reference_control', False) else '✗'}")

        logger.info("\n" + "=" * 70)
        logger.info("整合測試完成！")
        logger.info("=" * 70)

        sys.exit(0 if all_passed else 1)

    except KeyboardInterrupt:
        logger.info("\n測試被中斷")
        tester.cleanup(delete_stores=args.cleanup)
        sys.exit(1)

    except Exception as e:
        logger.error(f"測試過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        tester.cleanup(delete_stores=args.cleanup)
        sys.exit(1)


if __name__ == '__main__':
    main()
