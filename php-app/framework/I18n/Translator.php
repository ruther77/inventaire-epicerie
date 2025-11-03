<?php

declare(strict_types=1);

namespace Framework\I18n;

final class Translator
{
    private string $locale = 'en';

    private string $fallback = 'en';

    /** @var array<string, array<string, string>> */
    private array $catalogue = [];

    public function __construct(private readonly string $langPath)
    {
    }

    public function setLocale(string $locale): void
    {
        $this->locale = $locale;
        $this->loadLocale($locale);
    }

    public function setFallback(string $locale): void
    {
        $this->fallback = $locale;
        $this->loadLocale($locale);
    }

    public function locale(): string
    {
        return $this->locale;
    }

    public function get(string $key, array $replace = [], ?string $locale = null): string
    {
        $locale = $locale ?? $this->locale;
        $this->loadLocale($locale);

        $line = $this->catalogue[$locale][$key] ?? $this->catalogue[$this->fallback][$key] ?? $key;

        foreach ($replace as $search => $value) {
            $line = str_replace(':' . $search, (string) $value, $line);
        }

        return $line;
    }

    private function loadLocale(string $locale): void
    {
        if (isset($this->catalogue[$locale])) {
            return;
        }

        $file = rtrim($this->langPath, '/') . '/' . $locale . '/messages.php';
        if (is_file($file)) {
            /** @var array<string, string> $translations */
            $translations = require $file;
            $this->catalogue[$locale] = $translations;
        } else {
            $this->catalogue[$locale] = [];
        }
    }
}
