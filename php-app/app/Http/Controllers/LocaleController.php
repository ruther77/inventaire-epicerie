<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use Framework\Http\Response;
use Framework\I18n\Translator;

final class LocaleController extends Controller
{
    public function switch(string $locale): Response
    {
        /** @var Translator $translator */
        $translator = app()->get(Translator::class);
        $translator->setLocale($locale);
        $this->session()->setLocale($locale);
        $this->session()->flash('status', trans('messages.locale_switched', ['locale' => $locale]));

        return redirect('/');
    }
}
