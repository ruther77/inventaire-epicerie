<?php
declare(strict_types=1);

if (!defined('APP_ROOT')) {
    define('APP_ROOT', realpath(__DIR__));
}

if (!defined('APP_BASE_URL')) {
    $documentRoot = rtrim(str_replace('\\', '/', $_SERVER['DOCUMENT_ROOT'] ?? ''), '/');
    $appRoot = str_replace('\\', '/', APP_ROOT);
    $basePath = '';

    if ($documentRoot !== '') {
        $documentRootLength = strlen($documentRoot);

        if ($documentRootLength > 0 && strncmp($appRoot, $documentRoot, $documentRootLength) === 0) {
            $basePath = substr($appRoot, $documentRootLength);
        }
    }

    $basePath = '/' . ltrim($basePath, '/');
    if ($basePath !== '/' && substr($basePath, -1) !== '/') {
        $basePath .= '/';
    }

    define('APP_BASE_URL', $basePath);
}

if (!function_exists('asset')) {
    function asset(string $path): string
    {
        return APP_BASE_URL . ltrim($path, '/');
    }
}

if (!function_exists('url_for')) {
    function url_for(string $path): string
    {
        return APP_BASE_URL . ltrim($path, '/');
    }
}
