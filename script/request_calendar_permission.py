#!/usr/bin/env python3
"""カレンダーアクセス許可を明示的に要求するスクリプト"""

import logging
import sys
import time

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

try:
    import EventKit
    import Foundation

    logger.info("✅ EventKit フレームワークが利用可能です")
except ImportError:
    logger.error("❌ EventKit フレームワークが見つかりません")
    logger.error("   pyobjc-framework-EventKit をインストールしてください")
    sys.exit(1)


def request_calendar_access():
    """カレンダーアクセス許可を要求"""
    logger.info("🔐 カレンダーアクセス許可を要求中...")

    # EventStoreを作成
    event_store = EventKit.EKEventStore.alloc().init()

    # 現在のアクセス状態を確認
    auth_status = EventKit.EKEventStore.authorizationStatusForEntityType_(
        EventKit.EKEntityTypeEvent
    )

    status_messages = {
        EventKit.EKAuthorizationStatusNotDetermined: "未決定",
        EventKit.EKAuthorizationStatusRestricted: "制限あり",
        EventKit.EKAuthorizationStatusDenied: "拒否",
        EventKit.EKAuthorizationStatusAuthorized: "許可済み",
    }

    logger.info(f"📊 現在のアクセス状態: {status_messages.get(auth_status, '不明')}")

    if auth_status == EventKit.EKAuthorizationStatusAuthorized:
        logger.info("✅ カレンダーアクセスは既に許可されています")
        return True

    elif auth_status == EventKit.EKAuthorizationStatusDenied:
        logger.warning("❌ カレンダーアクセスが拒否されています")
        logger.info("   システム設定で手動で許可してください:")
        print_system_settings_path()
        return False

    elif auth_status == EventKit.EKAuthorizationStatusNotDetermined:

        # アクセス許可を要求（これでダイアログが表示される）
        def completion_handler(granted, error):
            if granted:
                pass
            else:
                if error:
                    pass

        # 非同期でアクセス許可を要求
        event_store.requestAccessToEntityType_completion_(
            EventKit.EKEntityTypeEvent, completion_handler
        )

        # 少し待機してユーザーの応答を待つ
        time.sleep(3)

        # 再度状態を確認
        new_auth_status = EventKit.EKEventStore.authorizationStatusForEntityType_(
            EventKit.EKEntityTypeEvent
        )

        if new_auth_status == EventKit.EKAuthorizationStatusAuthorized:
            return True
        else:
            print_system_settings_path()
            return False

    else:
        print_system_settings_path()
        return False


def print_system_settings_path():
    """システム設定のパスを表示"""

    # macOSバージョンを取得
    version = Foundation.NSProcessInfo.processInfo().operatingSystemVersion()
    major_version = version.majorVersion

    if major_version >= 13:  # Ventura以降
        pass
    else:  # Monterey以前
        pass



def test_calendar_access():
    """カレンダーアクセスをテスト"""

    try:
        event_store = EventKit.EKEventStore.alloc().init()
        calendars = event_store.calendarsForEntityType_(EventKit.EKEntityTypeEvent)


        for _calendar in calendars:
            pass

        return True

    except Exception:
        return False


if __name__ == "__main__":

    # アクセス許可を要求
    if request_calendar_access():
        # アクセステストを実行
        test_calendar_access()
    else:
        pass
