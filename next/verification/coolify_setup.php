<?php
// Run inside the original Coolify container; does not deploy or modify DNS.
require '/var/www/html/vendor/autoload.php';
$app = require '/var/www/html/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
$environment = App\Models\Environment::findOrFail(27);
if ($environment->project_id !== 26 || $environment->project->name !== 'Codifica') {
    throw new RuntimeException('Unexpected project');
}
if (App\Models\Application::where('environment_id', 27)->exists()) {
    throw new RuntimeException('Application already exists; inspect instead of duplicating');
}
$application = App\Models\Application::create([
    'name' => 'Codifica', 'description' => 'Private channels and docs for humans and existing agents',
    'environment_id' => 27, 'destination_type' => App\Models\StandaloneDocker::class, 'destination_id' => 0,
    'git_repository' => 'https://github.com/davidedicillo/codifica', 'git_branch' => 'codex/channels',
    'git_commit_sha' => 'HEAD', 'build_pack' => 'dockerfile', 'base_directory' => '/next',
    'dockerfile_location' => '/Dockerfile', 'ports_exposes' => '8000',
    'fqdn' => 'https://codifica.app', 'health_check_enabled' => false,
]);
$application->settings->is_auto_deploy_enabled = false;
$application->settings->save();
$application->refresh();
App\Models\LocalPersistentVolume::create([
    'name' => 'codifica-data', 'mount_path' => '/data', 'host_path' => '/data/codifica',
    'resource_type' => App\Models\Application::class, 'resource_id' => $application->id,
]);
foreach ([
    'CODIFICA_SECRET_KEY' => bin2hex(random_bytes(48)),
    'CODIFICA_ORIGIN' => 'https://codifica.app',
    'CODIFICA_DATABASE_PATH' => '/data/codifica.sqlite',
    'CODIFICA_PILOT_EMAILS' => 'davide@dicillo.com',
    'CODIFICA_EMAIL_FROM' => 'davide@dicillo.com',
] as $key => $value) {
    App\Models\EnvironmentVariable::create([
        'key' => $key, 'value' => $value, 'is_runtime' => true, 'is_buildtime' => false,
        'is_preview' => false, 'resourceable_type' => App\Models\Application::class,
        'resourceable_id' => $application->id,
    ]);
}
$application->custom_labels = str(implode('|coolify|', generateLabelsApplication($application)))->replace('|coolify|', "\n");
$application->save();
echo json_encode(['id' => $application->id, 'uuid' => $application->uuid]) . "\n";
