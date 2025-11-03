@extends('layouts.app')

@section('content')
<div class="max-w-3xl mx-auto py-16 text-center">
    <h1 class="text-4xl font-bold text-emerald-700 mb-4">{{ trans('messages.not_found') }}</h1>
    <p class="text-lg text-slate-600 mb-6">{{ trans('messages.not_found_description') }}</p>
    <a href="/" class="inline-flex items-center px-4 py-2 bg-emerald-600 text-white rounded-md hover:bg-emerald-700">{{ trans('messages.back_home') }}</a>
</div>
@endsection
