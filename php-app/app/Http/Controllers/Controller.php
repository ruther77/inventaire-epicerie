<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use Framework\Application\Application;
use Framework\Http\Request;
use Framework\Http\Response;
use Framework\Support\Session;

abstract class Controller
{
    protected Application $app;

    public function __construct()
    {
        $this->app = Application::getInstance();
    }

    protected function request(): Request
    {
        return $this->app->request();
    }

    protected function session(): Session
    {
        return $this->app->session();
    }

    protected function view(string $view, array $data = []): Response
    {
        return response(view($view, $data));
    }
}
