/**
 * @file Root application shell.
 * Loads product config from the Nexus API, owns BYOK settings (persisted to
 * localStorage) and sidebar visibility, and routes between Chat and Settings.
 */
import { useEffect, useMemo, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { getConfig, resolveProductConfig, setApiProductMode } from './api/client'
import { ChatPage } from './pages/ChatPage'
import { SettingsPage } from './pages/SettingsPage'
import { asProductMode, loadSettings, saveSettings } from './lib/settings'
import type { ProductConfig, ProductMode, SettingsState } from './types'

function applyProductChrome(cfg: ProductConfig, mode: ProductMode) {
  document.title = cfg.product_name
  document.documentElement.dataset.product = mode
  const favicon = document.querySelector<HTMLLinkElement>("link[rel='icon']")
  if (favicon) {
    favicon.type = mode === 'generic' ? 'image/svg+xml' : 'image/png'
    favicon.href =
      mode === 'generic' ? '/logos/generic.svg' : `/logos/${mode}-icon.png`
  }
}

/**
 * Top-level router and shared state provider for config + settings.
 */
export default function App() {
  const [catalog, setCatalog] = useState<ProductConfig | null>(null)
  const [settings, setSettings] = useState<SettingsState>(() => loadSettings())
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const productMode = asProductMode(settings.productMode)

  useEffect(() => {
    setApiProductMode(productMode)
    void getConfig().then((cfg) => setCatalog(cfg))
  }, [productMode])

  useEffect(() => {
    saveSettings(settings)
  }, [settings])

  const product = useMemo(() => {
    const base = catalog ?? {
      product_name: 'Nexus',
      product_short: 'Nexus',
      product_slug: 'nexus',
      docs_base_url: '',
      community_base_url: '',
      community_new_topic_url: '',
      github_org: '',
      logo_url: '/logos/mosip.png',
    }
    return resolveProductConfig(base, productMode)
  }, [catalog, productMode])

  useEffect(() => {
    applyProductChrome(product, productMode)
  }, [product, productMode])

  function handleProductMode(mode: ProductMode) {
    setSettings((prev) => ({ ...prev, productMode: mode }))
  }

  return (
    <Routes>
      <Route
        path="/"
        element={
          <ChatPage
            config={product}
            settings={settings}
            sidebarOpen={sidebarOpen}
            onToggleSidebar={() => setSidebarOpen((v) => !v)}
            onProductModeChange={handleProductMode}
          />
        }
      />
      <Route
        path="/settings"
        element={
          <SettingsPage
            config={product}
            settings={settings}
            onChange={setSettings}
          />
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
