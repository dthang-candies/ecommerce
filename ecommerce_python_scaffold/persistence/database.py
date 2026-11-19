class Database:
    """Điểm tích hợp database. Hiện chưa gắn SQLite/PostgreSQL/ORM."""

    def new_session(self):
        # TODO: tạo session/connection và quản lý vòng đời transaction.
        raise NotImplementedError
