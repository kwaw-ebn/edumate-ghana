export function write(kind:string,owner:string,id:string,data:any):Promise<any>;
export function read(kind:string,owner:string,id:string):Promise<any>;
export function list(kind:string,owner:string):Promise<Record<string,any>[]>;
export function remove(kind:string,owner:string,id:string):Promise<void>;
export function activate(user:Record<string,any>):void;
export function active():Record<string,any>|null;
export function queue(owner:string,kind:string,target:string,data?:Record<string,any>):Promise<any>;
export function synchronize(user:Record<string,any>,request:(path:string,method?:string,body?:any)=>Promise<any>):Promise<{sent:number,pending:number}>;
