<?php

declare(strict_types=1);

namespace Framework\Support;

final class Session
{
    private const FLASH_KEY = '_flash';

    /**
     * @var array{old:array<string,mixed>,errors:array<string,array<int,string>>,messages:array<string,mixed>}
     */
    private array $flashData = [
        'old' => [],
        'errors' => [],
        'messages' => [],
    ];

    public function __construct()
    {
        if (session_status() !== PHP_SESSION_ACTIVE) {
            session_start();
        }

        $flash = $_SESSION[self::FLASH_KEY] ?? [
            'old' => [],
            'errors' => [],
            'messages' => [],
        ];

        $this->flashData = $flash;
        $_SESSION[self::FLASH_KEY] = [
            'old' => [],
            'errors' => [],
            'messages' => [],
        ];
    }

    public function token(): string
    {
        if (empty($_SESSION['_token'])) {
            $_SESSION['_token'] = bin2hex(random_bytes(32));
        }

        return (string) $_SESSION['_token'];
    }

    public function validateCsrf(?string $token): bool
    {
        return hash_equals($this->token(), (string) $token);
    }

    public function flash(string $key, mixed $value): void
    {
        $_SESSION[self::FLASH_KEY]['messages'][$key] = $value;
    }

    public function setLocale(string $locale): void
    {
        $_SESSION['locale'] = $locale;
    }

    public function locale(): ?string
    {
        return $_SESSION['locale'] ?? null;
    }

    public function old(string $key, mixed $default = null): mixed
    {
        return $this->flashData['old'][$key] ?? $default;
    }

    public function setOld(array $data): void
    {
        $_SESSION[self::FLASH_KEY]['old'] = $data;
    }

    public function errors(): array
    {
        return $this->flashData['errors'] ?? [];
    }

    public function setErrors(array $errors): void
    {
        $_SESSION[self::FLASH_KEY]['errors'] = $errors;
    }

    public function message(string $key, mixed $default = null): mixed
    {
        $value = $this->flashData['messages'][$key] ?? $default;
        unset($this->flashData['messages'][$key]);

        return $value;
    }
}
