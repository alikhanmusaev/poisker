package ru.poisker.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import ru.poisker.app.util.UrlRules

class UrlRulesTest {
    @Test
    fun poiskerHttpsIsInternal() {
        assertTrue(UrlRules.isInternalHttpUrl("https://poisker.ru/"))
        assertTrue(UrlRules.isInternalHttpUrl("https://poisker.ru/posts/abc/"))
        assertTrue(UrlRules.isInternalHttpUrl("https://www.poisker.ru/accounts/login/"))
        assertTrue(UrlRules.shouldHandleInWebView("https://poisker.ru/"))
    }

    @Test
    fun externalHttpsIsExternal() {
        assertTrue(UrlRules.isExternalHttpUrl("https://google.com/"))
        assertFalse(UrlRules.shouldHandleInWebView("https://example.com/page"))
    }

    @Test
    fun telIsSpecialScheme() {
        assertTrue(UrlRules.isSpecialScheme("tel:+79001234567"))
        assertFalse(UrlRules.shouldHandleInWebView("tel:+79001234567"))
        assertEquals("tel", UrlRules.schemeOf("tel:+79001234567"))
    }

    @Test
    fun unknownSchemeIsNotInternal() {
        assertFalse(UrlRules.isInternalHttpUrl("ftp://poisker.ru/file"))
        assertFalse(UrlRules.shouldHandleInWebView("myapp://open"))
    }

    @Test
    fun subdomainIsAllowed() {
        assertTrue(UrlRules.isAllowedPoiskerHost("cdn.poisker.ru"))
        assertTrue(UrlRules.isInternalHttpUrl("https://media.poisker.ru/x.jpg"))
    }

    @Test
    fun releaseStartUrlIsHttpsPoisker() {
        assertTrue(UrlRules.START_URL.startsWith("https://poisker.ru"))
        assertFalse(UrlRules.START_URL.startsWith("http://"))
    }

    @Test
    fun whatsappAndTelegramAreSpecial() {
        assertTrue(UrlRules.isSpecialScheme("whatsapp://send?phone=79001234567"))
        assertTrue(UrlRules.isSpecialScheme("tg://resolve?domain=poisker"))
    }
}
