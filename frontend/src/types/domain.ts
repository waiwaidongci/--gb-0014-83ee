export type User={id:number;email:string;name:string;role:string};
export type Survey={id:number;name:string;survey_date:string;filename:string;description:string;transect_count:number};
export type Transect={id:number;survey_id:number;reference:string;name:string;habitat:string;counts:Record<string,number>;n:number};
export type DiversityRecord={id:number;reference:string;name:string;habitat:string;status:string;n:number;observed_species:number;rarefied:number|null;shannon:number|null;simpson:number|null;curve:{m:number;expected:number}[];intervals:{shannon_ci:number[];simpson_ci:number[];rarefied_ci:number[];method:string}|null;rare_species?:{species:string;count:number}[];reason?:string};
export type Run={id:number;name:string;survey_id:number;status:string;config:{transect_ids:number[];m:number;bootstrap:number;seed:number};result:{fingerprint?:string;m?:number;common_limit?:number;eligible?:number;excluded_empty?:number;bootstrap?:number;seed?:number;transects?:DiversityRecord[];definitions?:Record<string,string>};error?:string;created_at:string};
export type Note={id:number;name:string;run_id:number;transect_ids:number[];observation:string;suggested_action:string;status:string;review_note:string;created_at:string};
export type Audit={id:number;actor:string;action:string;detail:object;created_at:string};
