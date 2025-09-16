#!/usr/bin/env python3
"""カレンダーアクセス許可を明示的に要求するスクリプト"""

import sys
import time

try:
    import EventKit
    import Foundation

    print("✅ EventKit フレームワークが利用可能です")
except ImportError:
    print("❌ EventKit フレームワークが見つかりません")
    print("   pyobjc-framework-EventKit をインストールしてください")
    sys.exit(1)


def request_calendar_access():
    """カレンダーアクセス許可を要求"""
    print("🔐 カレンダーアクセス許可を要求中...")

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

    print(f"📊 現在のアクセス状態: {status_messages.get(auth_status, '不明')}")

    if auth_status == EventKit.EKAuthorizationStatusAuthorized:
        print("✅ カレンダーアクセスは既に許可されています")
        return True

    elif auth_status == EventKit.EKAuthorizationStatusDenied:
        print("❌ カレンダーアクセスが拒否されています")
        print("   システム設定で手動で許可してください:")
        print_system_settings_path()
        return False

    elif auth_status == EventKit.EKAuthorizationStatusNotDetermined:
        print("⏳ カレンダーアクセス許可ダイアログを表示します...")
        print("   ダイアログが表示されたら「OK」を選択してください")

        # アクセス許可を要求（これでダイアログが表示される）
        def completion_handler(granted, error):
            if granted:
                print("✅ カレンダーアクセスが許可されました！")
            else:
                print("❌ カレンダーアクセスが拒否されました")
                if error:
                    print(f"   エラー: {error}")

        # 非同期でアクセス許可を要求
        event_store.requestAccessToEntityType_completion_(
            EventKit.EKEntityTypeEvent, completion_handler
        )

        # 少し待機してユーザーの応答を待つ
        print("   ダイアログでの応答を待機中...")
        time.sleep(3)

        # 再度状態を確認
        new_auth_status = EventKit.EKEventStore.authorizationStatusForEntityType_(
            EventKit.EKEntityTypeEvent
        )

        if new_auth_status == EventKit.EKAuthorizationStatusAuthorized:
            print("✅ アクセス許可が完了しました！")
            return True
        else:
            print("⚠️  アクセス許可の状態を確認してください")
            print_system_settings_path()
            return False

    else:
        print("⚠️  制限されたアクセス状態です")
        print_system_settings_path()
        return False


def print_system_settings_path():
    """システム設定のパスを表示"""
    print("\n🔧 手動設定方法:")

    # macOSバージョンを取得
    version = Foundation.NSProcessInfo.processInfo().operatingSystemVersion()
    major_version = version.majorVersion

    if major_version >= 13:  # Ventura以降
        print("   1. システム設定を開く")
        print("   2. プライバシーとセキュリティ > カレンダー")
        print("   3. Pythonまたはターミナルのスイッチをオンにする")
    else:  # Monterey以前
        print("   1. システム環境設定を開く")
        print("   2. セキュリティとプライバシー > プライバシー > カレンダー")
        print("   3. Pythonまたはターミナルにチェックを入れる")

    print(f"\n💻 検出されたmacOSバージョン: {major_version}.x")


def test_calendar_access():
    """カレンダーアクセスをテスト"""
    print("\n🧪 カレンダーアクセステスト中...")

    try:
        event_store = EventKit.EKEventStore.alloc().init()
        calendars = event_store.calendarsForEntityType_(EventKit.EKEntityTypeEvent)

        print(f"📅 利用可能なカレンダー数: {len(calendars)}")

        for calendar in calendars:
            print(f"   • {calendar.title()} ({calendar.type()})")

        return True

    except Exception as e:
        print(f"❌ カレンダーアクセステストに失敗: {e}")
        return False


if __name__ == "__main__":
    print("🗓️  macOS Calendar アクセス許可テスト")
    print("=" * 50)

    # アクセス許可を要求
    if request_calendar_access():
        # アクセステストを実行
        test_calendar_access()
        print("\n✅ カレンダーアクセス設定が完了しました！")
        print("   これで MCP サーバーが正常に動作するはずです。")
    else:
        print("\n⚠️  カレンダーアクセス許可が必要です。")
        print("   上記の手動設定方法を試してください。")
