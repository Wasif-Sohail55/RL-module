"""Tests for ADO.NET connection string parsing in db.py"""
import pytest

from db import _parse_adonet_connection_string, _build_sqlalchemy_url


class TestParseAdonetConnectionString:
    def test_parse_basic_connection_string(self):
        conn_str = "Server=myserver;Database=mydb;User Id=myuser;Password=mypass;"
        result = _parse_adonet_connection_string(conn_str)
        assert result["Server"] == "myserver"
        assert result["Database"] == "mydb"
        assert result["User Id"] == "myuser"
        assert result["Password"] == "mypass"

    def test_parse_azure_connection_string(self):
        conn_str = (
            'Server=tcp:projectserver2181104.database.windows.net,1433;'
            'Initial Catalog=projectdatabase181104;Encrypt=True;'
            'TrustServerCertificate=False;Connection Timeout=30;'
            'Authentication="Active Directory Default";'
        )
        result = _parse_adonet_connection_string(conn_str)
        assert result["Server"] == "tcp:projectserver2181104.database.windows.net,1433"
        assert result["Initial Catalog"] == "projectdatabase181104"
        assert result["Encrypt"] == "True"
        assert result["TrustServerCertificate"] == "False"
        assert result["Connection Timeout"] == "30"
        assert result["Authentication"] == "Active Directory Default"

    def test_parse_handles_empty_parts(self):
        conn_str = "Server=myserver;;Database=mydb;"
        result = _parse_adonet_connection_string(conn_str)
        assert result["Server"] == "myserver"
        assert result["Database"] == "mydb"
        assert len(result) == 2


class TestBuildSqlalchemyUrl:
    def test_returns_sqlalchemy_url_unchanged(self):
        url = "mssql+pyodbc://user:pass@server/db"
        result = _build_sqlalchemy_url(url)
        assert result == url

    def test_returns_sqlite_url_unchanged(self):
        url = "sqlite+pysqlite:///:memory:"
        result = _build_sqlalchemy_url(url)
        assert result == url

    def test_converts_azure_ad_connection_string(self):
        conn_str = (
            'Server=tcp:projectserver2181104.database.windows.net,1433;'
            'Initial Catalog=projectdatabase181104;Encrypt=True;'
            'TrustServerCertificate=False;Connection Timeout=30;'
            'Authentication="Active Directory Default";'
        )
        result = _build_sqlalchemy_url(conn_str)
        
        # Check the URL structure
        assert result.startswith("mssql+pyodbc://")
        assert "projectserver2181104.database.windows.net:1433" in result
        assert "projectdatabase181104" in result
        assert "driver=ODBC+Driver+18+for+SQL+Server" in result
        assert "Encrypt=yes" in result
        assert "TrustServerCertificate=no" in result
        assert "Authentication=ActiveDirectoryDefault" in result
        assert "Connection Timeout=30" in result

    def test_converts_sql_auth_connection_string(self):
        conn_str = (
            "Server=myserver.database.windows.net,1433;"
            "Initial Catalog=mydb;"
            "User Id=myuser;"
            "Password=myp@ssword;"
        )
        result = _build_sqlalchemy_url(conn_str)
        
        assert result.startswith("mssql+pyodbc://")
        assert "myuser:" in result
        assert "myp%40ssword@" in result  # URL-encoded @
        assert "myserver.database.windows.net:1433" in result
        assert "mydb?" in result

    def test_handles_data_source_alias(self):
        conn_str = "Data Source=myserver;Database=mydb;"
        result = _build_sqlalchemy_url(conn_str)
        
        assert "myserver" in result
        assert "mydb" in result

    def test_default_port_when_not_specified(self):
        conn_str = "Server=myserver;Database=mydb;"
        result = _build_sqlalchemy_url(conn_str)
        
        assert "myserver:1433" in result
