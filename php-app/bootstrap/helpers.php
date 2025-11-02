<?php

declare(strict_types=1);

use Framework\Application\Application;
use Framework\View\ViewFactory;

define('BASE_PATH', dirname(__DIR__));

if (!function_exists('app')) {
    function app(): Application
    {
        return Application::getInstance();
    }
}

if (!function_exists('base_path')) {
    function base_path(string $path = ''): string
    {
        return BASE_PATH . ($path !== '' ? '/' . ltrim($path, '/') : '');
    }
}

if (!function_exists('config_path')) {
    function config_path(string $path = ''): string
    {
        return base_path('config' . ($path !== '' ? '/' . ltrim($path, '/') : ''));
    }
}

if (!function_exists('resource_path')) {
    function resource_path(string $path = ''): string
    {
        return base_path('resources' . ($path !== '' ? '/' . ltrim($path, '/') : ''));
    }
}

if (!function_exists('storage_path')) {
    function storage_path(string $path = ''): string
    {
        return base_path('storage' . ($path !== '' ? '/' . ltrim($path, '/') : ''));
    }
}

if (!function_exists('view')) {
    function view(string $view, array $data = []): string
    {
        return app()->get(ViewFactory::class)->make($view, $data);
    }
}

if (!function_exists('response')) {
    function response(string $content, int $status = 200, array $headers = []): Framework\Http\Response
    {
        return new Framework\Http\Response($content, $status, $headers);
    }
}

if (!function_exists('redirect')) {
    function redirect(string $path, int $status = 302): Framework\Http\Response
    {
        return Framework\Http\Response::redirect($path, $status);
    }
}

if (!function_exists('trans')) {
    function trans(string $key, array $replace = [], ?string $locale = null): string
    {
        return app()->get(Framework\I18n\Translator::class)->get($key, $replace, $locale);
    }
}

if (!function_exists('csrf_field')) {
    function csrf_field(): string
    {
        $token = app()->session()->token();

        return '<input type="hidden" name="_token" value="' . htmlspecialchars($token, ENT_QUOTES) . '">';
    }
}

if (!function_exists('old')) {
    function old(string $key, mixed $default = null): mixed
    {
        return app()->session()->old($key, $default);
    }
}

if (!function_exists('e')) {
    function e(string $value): string
    {
        return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    }
}

if (!function_exists('session')) {
    function session(): Framework\Support\Session
    {
        return app()->session();
    }
}
