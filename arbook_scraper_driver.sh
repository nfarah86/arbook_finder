#!/bin/sh

main(){
    # make a directory to store tsv file
    mkdir -p ${PROJECT_DATA_FOLDER}arbook/
    # go to this directory
    cd ${PROJECT_DATA_FOLDER}arbook/

    yesterday=`date -v-1d +%F`
    echo "Now processing $yesterday: $now";
    # we are getting 1 parameter: arbook_finder
    # get the min range you want to scrape the url
    range_min=$1
    # get the max range to scrape the url
    range_max=$2
    echo "bucket path:" ${S3_BUCKET_PATH}
    echo ${PROJECT_DATA_FOLDER}arbook/arbook_finder_${yesterday}.tsv

    # run script
    arbook_script=`${PROJECT_PYTHON_FOLDER}scrapers/arbook_finder_scraper.py ${range_min} ${range_max}`
    # zip tsv file located in specified file path
    if [ -s ${PROJECT_DATA_FOLDER}arbook/arbook_finder_${yesterday}.tsv ]; then
        gzip ${PROJECT_DATA_FOLDER}arbook/arbook_finder_${yesterday}.tsv
        # upload to s3
        aws_upload="${S3_CMD} --rr -c ${S3_CONFIG_PATH} put ${PROJECT_DATA_FOLDER}arbook/arbook_finder_${yesterday}.tsv.gz s3://${S3_BUCKET_PATH}/arbook/"
        $aws_upload
        #  sql statement
        sql="copy arbook_finder from 's3://${S3_BUCKET_PATH}/arbook/arbook_finder_${yesterday}.tsv.gz' CREDENTIALS 'aws_access_key_id=${AWS_ACCESS_KEY};aws_secret_access_key=${AWS_SECRET_KEY}' maxerror as 2 delimiter '\t' ACCEPTINVCHARS DATEFORMAT 'auto' TIMEFORMAT 'auto' gzip TRUNCATECOLUMNS;grant select on table arbook_finder to group analytics_users;"
        echo $sql
        # so here we can run the following to execute the above $sql.
        ${PROJECT_PYTHON_FOLDER}run_cmd.py "updating arbook_finder table" "$sql" ${PROJECT_CONF_REDSHIFT}
        # grant select permission to analytics_users
        ${PROJECT_PYTHON_FOLDER}run_cmd.py "granting select permission to arbook_finder table" "grant select on table arbook_finder to group analytics_users" ${PROJECT_CONF_REDSHIFT}
    else
        echo "there is no .tsv file"
        echo "No .tsv file for arbook_finder_scraper" | /usr/local/email/bin/email -s " arbook_finder_scraper error" -r smtp-relay.gmail.com -p 25 -f data-infra@udemy.com data-infra@udemy.com
        exit 0
    fi

}
# Loading config and running main

main $1 $2
