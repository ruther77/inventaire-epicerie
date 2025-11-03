<?php

declare(strict_types=1);

namespace Framework\Http;

final class Request
{
    public function __construct(
        public readonly string $method,
        public readonly string $path,
        public readonly array $query,
        public readonly array $body,
        public readonly array $headers
    ) {
    }

    public static function capture(): self
    {
        $method = strtoupper($_SERVER['REQUEST_METHOD'] ?? 'GET');
        $uri = $_SERVER['REQUEST_URI'] ?? '/';
        $path = parse_url($uri, PHP_URL_PATH) ?: '/';
        $query = $_GET ?? [];
        $body = $_POST ?? [];
        $headers = function_exists('getallheaders') ? (getallheaders() ?: []) : [];

        return new self($method, $path, $query, $body, $headers);
    }

    public function input(string $key, mixed $default = null): mixed
    {
        return $this->body[$key] ?? $this->query[$key] ?? $default;
    }

    public function only(array $keys): array
    {
        $data = [];
        foreach ($keys as $key) {
            if (array_key_exists($key, $this->body)) {
                $data[$key] = $this->body[$key];
            } elseif (array_key_exists($key, $this->query)) {
                $data[$key] = $this->query[$key];
            }
        }

        return $data;
    }
}
