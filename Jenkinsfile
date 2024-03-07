@Library('lib')_

pythonPipeline {
  package_name          = 'opensearch_stac_adapter'
  python_version        = '3.8'
  wheel_repo            = 'python-packages-public'
  create_tag_job        = true
  build_container_image = true
  dev_hosts             = 'docker-services-dev-01.vgt.vito.be'
  prod_hosts            = 'docker-services-prod-01.vgt.vito.be'
  docker_deploy         = true
  docker_run_options    = ['-p 8001:80']
}