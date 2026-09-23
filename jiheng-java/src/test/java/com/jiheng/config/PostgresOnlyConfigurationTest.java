package com.jiheng.config;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class PostgresOnlyConfigurationTest {
    @Test
    void configurationAndInitialMigrationDoNotReferenceSqlite() throws IOException {
        Path resources = Path.of("src", "main", "resources");
        String application = Files.readString(resources.resolve("application.yml"));
        String migration = Files.readString(resources.resolve("db/migration/V1__init_schema.sql"));

        assertTrue(application.contains("org.postgresql.Driver"));
        assertFalse(application.toLowerCase().contains("sqlite"));
        assertFalse(migration.toLowerCase().contains("autoincrement"));
        assertTrue(migration.contains("TIMESTAMPTZ"));
    }
}
