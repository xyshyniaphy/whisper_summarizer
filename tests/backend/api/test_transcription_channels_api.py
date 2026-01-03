"""
Transcription Channel Assignment API エンドポイントテスト

ユーザーがアクセス可能なチャンネル割り当て・変更・取得機能を検証する。
シナリオテスト：チャンネル変更・元に戻す・クリア・置換
"""

import pytest
import uuid
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.transcription import Transcription
from app.models.user import User
from app.models.channel import Channel, ChannelMembership, TranscriptionChannel


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def db_session() -> Session:
    """テスト用データベースセッション

    セッション終了時にロールバックを行い、テスト間のデータ汚染を防ぐ。
    """
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def test_client() -> TestClient:
    """認証なしのTestClient（認証テスト用）"""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def test_user(db_session: Session) -> dict:
    """テスト用一般ユーザーを作成"""
    uid = uuid.uuid4()
    user = User(
        id=uid,
        email=f"user-{str(uid)[:8]}@example.com",
        is_active=True,
        is_admin=False,
        activated_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return {
        "id": str(uid),
        "email": user.email,
        "raw_uuid": uid
    }


@pytest.fixture
def test_admin(db_session: Session) -> dict:
    """テスト用管理者ユーザーを作成"""
    uid = uuid.uuid4()
    user = User(
        id=uid,
        email=f"admin-{str(uid)[:8]}@example.com",
        is_active=True,
        is_admin=True,
        activated_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return {
        "id": str(uid),
        "email": user.email,
        "raw_uuid": uid
    }


@pytest.fixture
def other_user(db_session: Session) -> dict:
    """別のテスト用ユーザーを作成（権限テスト用）"""
    uid = uuid.uuid4()
    user = User(
        id=uid,
        email=f"other-{str(uid)[:8]}@example.com",
        is_active=True,
        is_admin=False,
        activated_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return {
        "id": str(uid),
        "email": user.email,
        "raw_uuid": uid
    }


@pytest.fixture
def user_auth_client(test_user: dict, db_session: Session) -> TestClient:
    """一般ユーザー認証済みTestClient"""
    from app.main import app
    from app.api.deps import get_current_db_user

    def override_get_current_db_user():
        return db_session.query(User).filter(User.id == test_user["raw_uuid"]).first()

    app.dependency_overrides[get_current_db_user] = override_get_current_db_user

    with TestClient(app) as client:
        yield client

    app.dependency_overrides = {}


@pytest.fixture
def admin_auth_client(test_admin: dict, db_session: Session) -> TestClient:
    """管理者認証済みTestClient"""
    from app.main import app
    from app.api.deps import get_current_db_user, require_admin

    def override_get_current_db_user():
        return db_session.query(User).filter(User.id == test_admin["raw_uuid"]).first()

    def override_require_admin():
        return db_session.query(User).filter(User.id == test_admin["raw_uuid"]).first()

    app.dependency_overrides[get_current_db_user] = override_get_current_db_user
    app.dependency_overrides[require_admin] = override_require_admin

    with TestClient(app) as client:
        yield client

    app.dependency_overrides = {}


@pytest.fixture
def other_auth_client(other_user: dict, db_session: Session) -> TestClient:
    """別ユーザー認証済みTestClient（権限テスト用）"""
    from app.main import app
    from app.api.deps import get_current_db_user

    def override_get_current_db_user():
        return db_session.query(User).filter(User.id == other_user["raw_uuid"]).first()

    app.dependency_overrides[get_current_db_user] = override_get_current_db_user

    with TestClient(app) as client:
        yield client

    app.dependency_overrides = {}


@pytest.fixture
def test_transcription(db_session: Session, test_user: dict) -> dict:
    """テスト用転写を作成"""
    trans_id = uuid.uuid4()
    transcription = Transcription(
        id=trans_id,
        user_id=test_user["raw_uuid"],
        file_name="test_audio.mp3",
        language="zh",
        duration_seconds=120,
        stage="completed"
    )
    db_session.add(transcription)
    db_session.commit()
    db_session.refresh(transcription)

    return {
        "id": str(transcription.id),
        "file_name": transcription.file_name
    }


@pytest.fixture
def test_channels(db_session: Session, test_admin: dict) -> list[dict]:
    """複数のテスト用チャンネルを作成（一意の名前を使用）"""
    channels = []
    suffix = uuid.uuid4().hex[:8]
    for i in range(3):
        channel = Channel(
            name=f"TestChannel_{suffix}_{i}",
            description=f"Test channel {i} description",
            created_by=test_admin["raw_uuid"]
        )
        db_session.add(channel)
        db_session.commit()
        db_session.refresh(channel)
        channels.append({
            "id": str(channel.id),
            "name": channel.name,
            "description": channel.description
        })
    return channels


# ==============================================================================
# GET /api/transcriptions/{id}/channels - Get Transcription Channels
# ==============================================================================

@pytest.mark.integration
class TestGetTranscriptionChannels:
    """転写のチャンネル取得エンドポイントテスト"""

    def test_get_channels_requires_authentication(self, test_client: TestClient) -> None:
        """認証なしでチャンネル取得するとエラーになるテスト"""
        response = test_client.get(f"/api/transcriptions/{uuid.uuid4()}/channels")
        assert response.status_code in [401, 403]

    def test_get_channels_invalid_transcription_id(self, user_auth_client: TestClient) -> None:
        """無効な転写IDで422を返すテスト"""
        response = user_auth_client.get("/api/transcriptions/invalid-uuid/channels")
        assert response.status_code == 422
        assert "Invalid transcription ID format" in response.json()["detail"]

    def test_get_channels_nonexistent_transcription(self, user_auth_client: TestClient) -> None:
        """存在しない転写IDで404を返すテスト"""
        non_existent = str(uuid.uuid4())
        response = user_auth_client.get(f"/api/transcriptions/{non_existent}/channels")
        assert response.status_code == 404

    def test_get_channels_no_assignments(self, user_auth_client: TestClient, test_transcription: dict) -> None:
        """チャンネル割り当てなしで空リストを返すテスト"""
        response = user_auth_client.get(f"/api/transcriptions/{test_transcription['id']}/channels")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_channels_with_assignments(self, user_auth_client: TestClient, test_transcription: dict,
                                          test_channels: list[dict], db_session: Session) -> None:
        """チャンネル割り当てありで正しく返すテスト"""
        # チャンネルに割り当て
        for channel in test_channels[:2]:
            assignment = TranscriptionChannel(
                transcription_id=uuid.UUID(test_transcription["id"]),
                channel_id=uuid.UUID(channel["id"])
            )
            db_session.add(assignment)
        db_session.commit()

        response = user_auth_client.get(f"/api/transcriptions/{test_transcription['id']}/channels")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["name"] in [c["name"] for c in test_channels[:2]]

    def test_get_channels_other_user_forbidden(self, other_auth_client: TestClient,
                                               test_transcription: dict, test_channels: list[dict],
                                               db_session: Session) -> None:
        """他ユーザーの転写チャンネルを取得できないテスト"""
        # チャンネルに割り当て
        assignment = TranscriptionChannel(
            transcription_id=uuid.UUID(test_transcription["id"]),
            channel_id=uuid.UUID(test_channels[0]["id"])
        )
        db_session.add(assignment)
        db_session.commit()

        # 他ユーザーはチャンネルメンバーでないのでアクセス不可
        response = other_auth_client.get(f"/api/transcriptions/{test_transcription['id']}/channels")
        assert response.status_code == 403

    def test_get_channels_channel_member_can_access(self, other_auth_client: TestClient,
                                                    test_transcription: dict, test_channels: list[dict],
                                                    db_session: Session, other_user: dict) -> None:
        """チャンネルメンバーは転写チャンネルを取得できるテスト"""
        # チャンネルに転写を割り当て
        assignment = TranscriptionChannel(
            transcription_id=uuid.UUID(test_transcription["id"]),
            channel_id=uuid.UUID(test_channels[0]["id"])
        )
        db_session.add(assignment)

        # 他ユーザーをチャンネルメンバーにする
        membership = ChannelMembership(
            channel_id=uuid.UUID(test_channels[0]["id"]),
            user_id=other_user["raw_uuid"]
        )
        db_session.add(membership)
        db_session.commit()

        # チャンネルメンバーはアクセス可能
        response = other_auth_client.get(f"/api/transcriptions/{test_transcription['id']}/channels")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == test_channels[0]["name"]

    def test_admin_can_get_any_transcription_channels(self, admin_auth_client: TestClient,
                                                     test_transcription: dict, test_channels: list[dict],
                                                     db_session: Session) -> None:
        """管理者はすべての転写チャンネルを取得できるテスト"""
        # チャンネルに割り当て
        assignment = TranscriptionChannel(
            transcription_id=uuid.UUID(test_transcription["id"]),
            channel_id=uuid.UUID(test_channels[0]["id"])
        )
        db_session.add(assignment)
        db_session.commit()

        response = admin_auth_client.get(f"/api/transcriptions/{test_transcription['id']}/channels")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1


# ==============================================================================
# POST /api/transcriptions/{id}/channels - Assign Transcription to Channels
# ==============================================================================

@pytest.mark.integration
class TestAssignTranscriptionToChannels:
    """転写のチャンネル割り当てエンドポイントテスト"""

    def test_assign_requires_authentication(self, test_client: TestClient) -> None:
        """認証なしで割り当てるとエラーになるテスト"""
        response = test_client.post(f"/api/transcriptions/{uuid.uuid4()}/channels", json={"channel_ids": []})
        assert response.status_code in [401, 403]

    def test_assign_invalid_transcription_id(self, user_auth_client: TestClient) -> None:
        """無効な転写IDで422を返すテスト"""
        response = user_auth_client.post("/api/transcriptions/invalid-uuid/channels", json={"channel_ids": []})
        assert response.status_code == 422
        assert "Invalid transcription ID format" in response.json()["detail"]

    def test_assign_nonexistent_transcription(self, user_auth_client: TestClient, test_channels: list[dict]) -> None:
        """存在しない転写IDで404を返すテスト"""
        non_existent = str(uuid.uuid4())
        response = user_auth_client.post(
            f"/api/transcriptions/{non_existent}/channels",
            json={"channel_ids": [test_channels[0]["id"]]}
        )
        assert response.status_code == 404

    def test_assign_to_single_channel(self, user_auth_client: TestClient, test_transcription: dict,
                                      test_channels: list[dict], db_session: Session) -> None:
        """単一チャンネルに割り当てるテスト"""
        response = user_auth_client.post(
            f"/api/transcriptions/{test_transcription['id']}/channels",
            json={"channel_ids": [test_channels[0]["id"]]}
        )
        assert response.status_code == 200
        data = response.json()
        assert "channel_ids" in data
        assert len(data["channel_ids"]) == 1
        assert data["channel_ids"][0] == test_channels[0]["id"]

        # DB確認
        assignments = db_session.query(TranscriptionChannel).filter(
            TranscriptionChannel.transcription_id == uuid.UUID(test_transcription["id"])
        ).all()
        assert len(assignments) == 1
        assert str(assignments[0].channel_id) == test_channels[0]["id"]

    def test_assign_to_multiple_channels(self, user_auth_client: TestClient, test_transcription: dict,
                                        test_channels: list[dict], db_session: Session) -> None:
        """複数チャンネルに割り当てるテスト"""
        channel_ids = [c["id"] for c in test_channels[:2]]
        response = user_auth_client.post(
            f"/api/transcriptions/{test_transcription['id']}/channels",
            json={"channel_ids": channel_ids}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["channel_ids"]) == 2

        # DB確認
        assignments = db_session.query(TranscriptionChannel).filter(
            TranscriptionChannel.transcription_id == uuid.UUID(test_transcription["id"])
        ).all()
        assert len(assignments) == 2

    def test_assign_clears_existing_assignments(self, user_auth_client: TestClient, test_transcription: dict,
                                               test_channels: list[dict], db_session: Session) -> None:
        """既存の割り当てをクリアして新しい割り当てに置き換えるテスト"""
        # 最初にチャンネル1に割り当て
        assignment = TranscriptionChannel(
            transcription_id=uuid.UUID(test_transcription["id"]),
            channel_id=uuid.UUID(test_channels[0]["id"])
        )
        db_session.add(assignment)
        db_session.commit()

        # チャンネル2に変更（チャンネル1はクリアされる）
        response = user_auth_client.post(
            f"/api/transcriptions/{test_transcription['id']}/channels",
            json={"channel_ids": [test_channels[1]["id"]]}
        )
        assert response.status_code == 200

        # DB確認：チャンネル1は削除、チャンネル2のみが存在
        assignments = db_session.query(TranscriptionChannel).filter(
            TranscriptionChannel.transcription_id == uuid.UUID(test_transcription["id"])
        ).all()
        assert len(assignments) == 1
        assert str(assignments[0].channel_id) == test_channels[1]["id"]

    def test_assign_clears_all_assignments(self, user_auth_client: TestClient, test_transcription: dict,
                                          test_channels: list[dict], db_session: Session) -> None:
        """空リストで全割り当てをクリアするテスト"""
        # 最初にチャンネルに割り当て
        assignment = TranscriptionChannel(
            transcription_id=uuid.UUID(test_transcription["id"]),
            channel_id=uuid.UUID(test_channels[0]["id"])
        )
        db_session.add(assignment)
        db_session.commit()

        # 空リストでクリア
        response = user_auth_client.post(
            f"/api/transcriptions/{test_transcription['id']}/channels",
            json={"channel_ids": []}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["channel_ids"]) == 0

        # DB確認：全て削除
        assignments = db_session.query(TranscriptionChannel).filter(
            TranscriptionChannel.transcription_id == uuid.UUID(test_transcription["id"])
        ).all()
        assert len(assignments) == 0

    def test_assign_other_user_transcription_forbidden(self, other_auth_client: TestClient,
                                                      test_transcription: dict, test_channels: list[dict]) -> None:
        """他ユーザーの転写を割り当てできないテスト"""
        response = other_auth_client.post(
            f"/api/transcriptions/{test_transcription['id']}/channels",
            json={"channel_ids": [test_channels[0]["id"]]}
        )
        assert response.status_code == 403

    def test_admin_can_assign_any_transcription(self, admin_auth_client: TestClient,
                                               test_transcription: dict, test_channels: list[dict],
                                               db_session: Session) -> None:
        """管理者はすべての転写を割り当てできるテスト"""
        response = admin_auth_client.post(
            f"/api/transcriptions/{test_transcription['id']}/channels",
            json={"channel_ids": [test_channels[0]["id"]]}
        )
        assert response.status_code == 200

        # DB確認
        assignments = db_session.query(TranscriptionChannel).filter(
            TranscriptionChannel.transcription_id == uuid.UUID(test_transcription["id"])
        ).all()
        assert len(assignments) == 1


# ==============================================================================
# Scenario Tests: Change Channels and Change Back
# ==============================================================================

@pytest.mark.integration
class TestChannelChangeScenarios:
    """チャンネル変更シナリオテスト

    ユーザーリクエスト：「チャンネルが存在しない場合は作成し、存在する場合は使用する。
    新しいチャンネルに変更し、元に戻す」
    """

    def test_scenario_create_channels_if_not_exist_and_assign(self, admin_auth_client: TestClient,
                                                              test_transcription: dict,
                                                              test_admin: dict, db_session: Session) -> None:
        """チャンネルが存在しない場合に作成して割り当てるシナリオテスト"""
        # 一意のチャンネル名を生成
        unique_channel_name = f"NewChannel_{uuid.uuid4().hex[:8]}"

        # チャンネルが存在しないことを確認
        existing = db_session.query(Channel).filter(Channel.name == unique_channel_name).first()
        assert existing is None

        # 管理者APIでチャンネル作成
        create_response = admin_auth_client.post("/api/admin/channels", json={
            "name": unique_channel_name,
            "description": "Created during test"
        })
        assert create_response.status_code == 200
        new_channel = create_response.json()

        # ユーザーAPIで転写を新チャンネルに割り当て
        assign_response = admin_auth_client.post(
            f"/api/transcriptions/{test_transcription['id']}/channels",
            json={"channel_ids": [new_channel["id"]]}
        )
        assert assign_response.status_code == 200

        # 割り当て確認
        response = admin_auth_client.get(f"/api/transcriptions/{test_transcription['id']}/channels")
        assert response.status_code == 200
        channels = response.json()
        assert len(channels) == 1
        assert channels[0]["name"] == unique_channel_name

    def test_scenario_use_existing_channels_and_assign(self, admin_auth_client: TestClient,
                                                       test_transcription: dict, test_channels: list[dict],
                                                       db_session: Session) -> None:
        """既存チャンネルを使用して割り当てるシナリオテスト"""
        # 既存チャンネルのIDを取得
        existing_channel_ids = [c["id"] for c in test_channels]

        # 既存チャンネルに割り当て
        response = admin_auth_client.post(
            f"/api/transcriptions/{test_transcription['id']}/channels",
            json={"channel_ids": existing_channel_ids}
        )
        assert response.status_code == 200

        # 割り当て確認
        assignments = db_session.query(TranscriptionChannel).filter(
            TranscriptionChannel.transcription_id == uuid.UUID(test_transcription["id"])
        ).all()
        assert len(assignments) == len(test_channels)

    def test_scenario_change_to_new_channel(self, user_auth_client: TestClient, test_transcription: dict,
                                           test_channels: list[dict], db_session: Session) -> None:
        """新しいチャンネルに変更するシナリオテスト"""
        # 最初にチャンネル1に割り当て
        user_auth_client.post(
            f"/api/transcriptions/{test_transcription['id']}/channels",
            json={"channel_ids": [test_channels[0]["id"]]}
        )

        # チャンネル2に変更
        response = user_auth_client.post(
            f"/api/transcriptions/{test_transcription['id']}/channels",
            json={"channel_ids": [test_channels[1]["id"]]}
        )
        assert response.status_code == 200

        # 変更確認：チャンネル1が削除、チャンネル2が追加
        assignments = db_session.query(TranscriptionChannel).filter(
            TranscriptionChannel.transcription_id == uuid.UUID(test_transcription["id"])
        ).all()
        assert len(assignments) == 1
        assert str(assignments[0].channel_id) == test_channels[1]["id"]

    def test_scenario_change_back_to_original_channel(self, user_auth_client: TestClient,
                                                      test_transcription: dict, test_channels: list[dict],
                                                      db_session: Session) -> None:
        """元のチャンネルに戻すシナリオテスト"""
        # チャンネル1に割り当て
        user_auth_client.post(
            f"/api/transcriptions/{test_transcription['id']}/channels",
            json={"channel_ids": [test_channels[0]["id"]]}
        )

        # チャンネル2に変更
        user_auth_client.post(
            f"/api/transcriptions/{test_transcription['id']}/channels",
            json={"channel_ids": [test_channels[1]["id"]]}
        )

        # 元のチャンネル1に戻す
        response = user_auth_client.post(
            f"/api/transcriptions/{test_transcription['id']}/channels",
            json={"channel_ids": [test_channels[0]["id"]]}
        )
        assert response.status_code == 200

        # 戻されたことを確認
        assignments = db_session.query(TranscriptionChannel).filter(
            TranscriptionChannel.transcription_id == uuid.UUID(test_transcription["id"])
        ).all()
        assert len(assignments) == 1
        assert str(assignments[0].channel_id) == test_channels[0]["id"]

    def test_scenario_full_cycle_no_channels_to_channel1_to_channel2_to_none(self,
                                                                              user_auth_client: TestClient,
                                                                              test_transcription: dict,
                                                                              test_channels: list[dict],
                                                                              db_session: Session) -> None:
        """完全サイクル：未割り当て→チャンネル1→チャンネル2→クリア"""
        # 1. 未割り当て状態を確認
        response = user_auth_client.get(f"/api/transcriptions/{test_transcription['id']}/channels")
        assert response.status_code == 200
        assert len(response.json()) == 0

        # 2. チャンネル1に割り当て
        response = user_auth_client.post(
            f"/api/transcriptions/{test_transcription['id']}/channels",
            json={"channel_ids": [test_channels[0]["id"]]}
        )
        assert response.status_code == 200
        assignments = db_session.query(TranscriptionChannel).filter(
            TranscriptionChannel.transcription_id == uuid.UUID(test_transcription["id"])
        ).all()
        assert len(assignments) == 1

        # 3. チャンネル2に変更
        response = user_auth_client.post(
            f"/api/transcriptions/{test_transcription['id']}/channels",
            json={"channel_ids": [test_channels[1]["id"]]}
        )
        assert response.status_code == 200
        assignments = db_session.query(TranscriptionChannel).filter(
            TranscriptionChannel.transcription_id == uuid.UUID(test_transcription["id"])
        ).all()
        assert len(assignments) == 1
        assert str(assignments[0].channel_id) == test_channels[1]["id"]

        # 4. クリア
        response = user_auth_client.post(
            f"/api/transcriptions/{test_transcription['id']}/channels",
            json={"channel_ids": []}
        )
        assert response.status_code == 200
        assignments = db_session.query(TranscriptionChannel).filter(
            TranscriptionChannel.transcription_id == uuid.UUID(test_transcription["id"])
        ).all()
        assert len(assignments) == 0

    def test_scenario_multiple_channels_swap(self, user_auth_client: TestClient, test_transcription: dict,
                                            test_channels: list[dict], db_session: Session) -> None:
        """複数チャンネルの交換テスト"""
        # チャンネル1と2に割り当て
        user_auth_client.post(
            f"/api/transcriptions/{test_transcription['id']}/channels",
            json={"channel_ids": [test_channels[0]["id"], test_channels[1]["id"]]}
        )

        # チャンネル3に変更（1と2は削除）
        response = user_auth_client.post(
            f"/api/transcriptions/{test_transcription['id']}/channels",
            json={"channel_ids": [test_channels[2]["id"]]}
        )
        assert response.status_code == 200

        assignments = db_session.query(TranscriptionChannel).filter(
            TranscriptionChannel.transcription_id == uuid.UUID(test_transcription["id"])
        ).all()
        assert len(assignments) == 1
        assert str(assignments[0].channel_id) == test_channels[2]["id"]
