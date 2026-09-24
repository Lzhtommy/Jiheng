package com.jiheng.util;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class BcryptUtilTest {
    @Test
    void hashesAndVerifiesPassword() {
        BcryptUtil bcrypt = new BcryptUtil();
        String hash = bcrypt.hash("correct horse battery staple");

        assertTrue(bcrypt.verify("correct horse battery staple", hash));
        assertFalse(bcrypt.verify("incorrect", hash));
    }
}
