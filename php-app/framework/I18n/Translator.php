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

        $this->loadLocale($this->fallback);

        $line = $this->valueForKey($this->catalogue[$locale], $key)
            ?? $this->valueForKey($this->catalogue[$this->fallback], $key)
            ?? $key;

        foreach ($replace as $search => $value) {
            $line = str_replace(':' . $search, (string) $value, $line);
        }

        return $line;
    }

    /**
     * @param array<string, mixed> $catalogue
     */
    private function valueForKey(array $catalogue, string $key): ?string
    {
        if (array_key_exists($key, $catalogue) && is_string($catalogue[$key])) {
            return $catalogue[$key];
        }

        $segments = explode('.', $key);
        $value = $catalogue;

        foreach ($segments as $segment) {
            if (!is_array($value) || !array_key_exists($segment, $value)) {
                return null;
            }

            $value = $value[$segment];
        }

        return is_string($value) ? $value : null;
    }

    private function loadLocale(string $locale): void
    {
        if (isset($this->catalogue[$locale])) {
            return;
        }

        $directory = rtrim($this->langPath, '/') . '/' . $locale;
        if (!is_dir($directory)) {
            $this->catalogue[$locale] = [];

            return;
        }

        $catalogue = [];

        /** @var string[] $files */
        $files = glob($directory . '/*.php') ?: [];
        foreach ($files as $file) {
            $name = basename($file, '.php');

            /** @var array<string, mixed> $translations */
            $translations = require $file;
            if (is_array($translations)) {
                $catalogue[$name] = $translations;
            }
        }

        $this->catalogue[$locale] = $catalogue;
    }
}
