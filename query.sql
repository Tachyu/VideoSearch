-- Select rows from a Table or View 'TableOrViewName' in schema 'SchemaName'
SELECT
	* 
FROM
	"public"."SceneInfo" 
WHERE
	"public"."SceneInfo"."SceneId" = ( 
        SELECT 
            "public"."PicInfo"."SceenId" 
        FROM 
            "public"."PicInfo" 
        WHERE 
            "public"."PicInfo"."PicFeatId" = 101 );


SELECT
	* 
FROM
	"public"."SceneInfo" 
WHERE
	"public"."SceneInfo"."SceneId" = (
SELECT
	"PicInfo"."SceenId"
FROM
	"public"."PicInfo" 
    WHERE 
    "PicFeatId"= ( 
	SELECT 
	"public"."FaceInfo"."PicId" 
	FROM 
	"public"."FaceInfo" 
	WHERE 
	"public"."FaceInfo"."FaceFeatId" = 339 ));


SELECT
	"public"."VideoId"."VideoId",
	"public"."VideoId"."VideoName",
	"public"."VideoInfo"."Length",
	"public"."VideoInfo"."Descrption" 
FROM
	"public"."VideoInfo",
	"public"."VideoId" 
WHERE
	"public"."VideoId"."VideoId" = 88 
	AND "public"."VideoInfo"."VideoId" = "public"."VideoId"."VideoId"


SELECT
	"public"."SceneInfo"."SceneId",
    "public"."VideoId"."VideoName",
    "public"."SceneInfo"."StartTime",
    "public"."SceneInfo"."Length"
FROM
	"public"."SceneInfo", 
    "public"."VideoId"
WHERE
	"public"."SceneInfo"."SceneId" = ( 
        SELECT 
            "public"."PicInfo"."SceenId" 
        FROM 
            "public"."PicInfo" 
        WHERE 
            "public"."PicInfo"."PicFeatId" = 101 )
    AND "public"."SceneInfo"."VideoId"="public"."VideoId"."VideoId";


SELECT
	"public"."SceneInfo"."SceneId",
    "public"."VideoId"."VideoName",
    "public"."SceneInfo"."StartTime",
    "public"."SceneInfo"."Length"
FROM
	"public"."SceneInfo",
    "public"."VideoId" 
WHERE
	"public"."SceneInfo"."SceneId" = (
SELECT
	"PicInfo"."SceenId"
FROM
	"public"."PicInfo" 
    WHERE 
    "PicFeatId"= ( 
	SELECT 
	"public"."FaceInfo"."PicId" 
	FROM 
	"public"."FaceInfo" 
	WHERE 
	"public"."FaceInfo"."FaceFeatId" = 339 ))
    AND "public"."SceneInfo"."VideoId"="public"."VideoId"."VideoId";


SELECT
	"public"."SceneInfo"."SceneId",
    "public"."VideoId"."VideoId",
    "public"."VideoId"."VideoName",
    "public"."SceneInfo"."StartTime",
    "public"."SceneInfo"."Length"
FROM
	"public"."SceneInfo",
    "public"."VideoId" 
WHERE
	"public"."SceneInfo"."SceneId" = (
SELECT
	"public"."PicInfo"."SceenId"
FROM
	"public"."PicInfo" 
    WHERE 
    "public"."PicInfo"."PicFeatId"= ( 
	SELECT 
	"public"."FaceInfo"."PicId" 
	FROM 
	"public"."FaceInfo" 
	WHERE 
	"public"."FaceInfo"."FaceFeatId" = picid ))
    AND "public"."SceneInfo"."VideoId"="public"."VideoId"."VideoId" ;
